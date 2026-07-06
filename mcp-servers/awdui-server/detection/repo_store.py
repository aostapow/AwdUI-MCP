"""SQLite-backed object repository store (QTP/UFT-style)."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional

_DATA_DIR = Path.home() / ".awdui-mcp"
_DB_PATH = _DATA_DIR / "repository.db"
_ASSETS_DIR = _DATA_DIR / "repository-assets"
_LEGACY_JSON_DIR = _DATA_DIR / "repositories"
_LEGACY_JSON_BAK = _DATA_DIR / "repositories.json.bak"

_lock = threading.Lock()
_migrated = False
_migrating = False

_SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS applications (
  app_id TEXT PRIMARY KEY,
  app_name TEXT NOT NULL,
  exe_path TEXT DEFAULT '',
  framework TEXT DEFAULT 'unknown',
  agent_hints TEXT DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS windows (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  app_id TEXT NOT NULL REFERENCES applications(app_id) ON DELETE CASCADE,
  window_key TEXT NOT NULL,
  title_pattern TEXT DEFAULT '',
  display_name TEXT DEFAULT '',
  agent_hints TEXT DEFAULT '',
  UNIQUE(app_id, window_key)
);

CREATE TABLE IF NOT EXISTS objects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  window_id INTEGER NOT NULL REFERENCES windows(id) ON DELETE CASCADE,
  repo_path TEXT NOT NULL UNIQUE,
  logical_name TEXT NOT NULL,
  object_key TEXT NOT NULL,
  parent_key TEXT DEFAULT '',
  swf_class TEXT DEFAULT 'SwfObject',
  automation_id TEXT DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS object_properties (
  object_id INTEGER PRIMARY KEY REFERENCES objects(id) ON DELETE CASCADE,
  full_properties TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS object_identification (
  object_id INTEGER PRIMARY KEY REFERENCES objects(id) ON DELETE CASCADE,
  mandatory TEXT NOT NULL DEFAULT '{}',
  assistive TEXT NOT NULL DEFAULT '{}',
  smart TEXT NOT NULL DEFAULT '{}',
  ordinal TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS object_snapshots (
  object_id INTEGER PRIMARY KEY REFERENCES objects(id) ON DELETE CASCADE,
  latest TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS object_resolution (
  object_id INTEGER PRIMARY KEY REFERENCES objects(id) ON DELETE CASCADE,
  layer TEXT DEFAULT '',
  backend TEXT DEFAULT '',
  method TEXT DEFAULT '',
  bbox TEXT DEFAULT '{}',
  success_count INTEGER DEFAULT 0,
  last_success TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS agent_hints (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scope TEXT NOT NULL,
  scope_id TEXT NOT NULL,
  hints TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL,
  UNIQUE(scope, scope_id)
);

CREATE INDEX IF NOT EXISTS idx_objects_automation ON objects(automation_id);
CREATE INDEX IF NOT EXISTS idx_objects_logical ON objects(logical_name);
CREATE INDEX IF NOT EXISTS idx_objects_window ON objects(window_id);
CREATE INDEX IF NOT EXISTS idx_windows_app ON windows(app_id);
"""


def app_id(app_name: str, exe_path: str = "") -> str:
    raw = exe_path or app_name
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _object_count_for_app(conn, aid: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM objects o "
        "JOIN windows w ON o.window_id=w.id WHERE w.app_id=?",
        (aid,),
    ).fetchone()
    return int(row["c"]) if row else 0


def _resolve_lookup_app_id(
    app_name: str,
    exe_path: str = "",
    *,
    conn,
) -> str:
    """Pick the app_id that actually has stored objects.

    Objects are often keyed by process name (``app_id(name, "")``) while live
    detection supplies a full ``exe_path`` hash — fall back when the exe-keyed
    app is empty or missing.
    """
    candidates: list[str] = []
    if exe_path:
        candidates.append(app_id(app_name, exe_path))
    name_id = app_id(app_name, "")
    if name_id not in candidates:
        candidates.append(name_id)

    best_id = candidates[0]
    best_count = -1
    for aid in candidates:
        app = conn.execute("SELECT 1 FROM applications WHERE app_id=?", (aid,)).fetchone()
        if not app:
            continue
        count = _object_count_for_app(conn, aid)
        if count > best_count:
            best_count = count
            best_id = aid
    return best_id


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)


def _json_loads(raw: Optional[str], default: Any = None) -> Any:
    if not raw:
        return default if default is not None else {}
    try:
        return json.loads(raw)
    except Exception:
        return default if default is not None else {}


@contextmanager
def _connect(db_path: Optional[Path] = None):
    path = db_path or _DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Optional[Path] = None) -> None:
    with _connect(db_path) as conn:
        conn.executescript(_SCHEMA)


def _ensure_migrated(db_path: Optional[Path] = None) -> None:
    global _migrated
    if _migrated or _migrating:
        init_db(db_path)
        return
    with _lock:
        if _migrated or _migrating:
            init_db(db_path)
            return
        init_db(db_path)
        migrate_json_repos(db_path=db_path, force=False)
        _migrated = True


def assets_dir(app_id_value: str) -> Path:
    d = _ASSETS_DIR / app_id_value
    d.mkdir(parents=True, exist_ok=True)
    return d


def assets_root() -> Path:
    _ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    return _ASSETS_DIR


def assets_path(app_id_value: str, filename: str) -> Path:
    return assets_dir(app_id_value) / filename


def relative_asset(app_id_value: str, filename: str) -> str:
    return f"{app_id_value}/{filename}"


def normalize_asset_rel(rel: str) -> str:
    """Fix legacy paths like app_id/assets/file.png → app_id/file.png when needed."""
    path = rel.replace("\\", "/").lstrip("/")
    parts = path.split("/")
    if len(parts) >= 3 and parts[1] == "assets":
        candidate = "/".join([parts[0]] + parts[2:])
        if assets_path(parts[0], "/".join(parts[2:])).is_file():
            return candidate
    if assets_root().joinpath(*path.split("/")).is_file():
        return path
    if len(parts) >= 2 and parts[1] != "assets":
        legacy = "/".join([parts[0], "assets"] + parts[1:])
        if assets_root().joinpath(*legacy.split("/")).is_file():
            return legacy
    return path


def _normalize_snapshot(snapshot: dict) -> dict:
    if not snapshot:
        return snapshot
    images = snapshot.get("images")
    if isinstance(images, dict):
        snapshot = dict(snapshot)
        snapshot["images"] = {
            k: normalize_asset_rel(str(v)) for k, v in images.items() if v
        }
    return snapshot


def _ensure_application(
    conn: sqlite3.Connection,
    aid: str,
    app_name: str,
    exe_path: str = "",
    framework: str = "unknown",
) -> None:
    now = _now()
    row = conn.execute("SELECT app_id FROM applications WHERE app_id=?", (aid,)).fetchone()
    if row:
        conn.execute(
            "UPDATE applications SET app_name=?, exe_path=?, framework=?, updated_at=? WHERE app_id=?",
            (app_name, exe_path, framework, now, aid),
        )
    else:
        conn.execute(
            "INSERT INTO applications (app_id, app_name, exe_path, framework, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (aid, app_name, exe_path, framework, now, now),
        )


def _ensure_window(
    conn: sqlite3.Connection,
    aid: str,
    window_key: str,
    title_pattern: str = "",
) -> int:
    row = conn.execute(
        "SELECT id FROM windows WHERE app_id=? AND window_key=?",
        (aid, window_key),
    ).fetchone()
    if row:
        return int(row["id"])
    pattern = title_pattern or f".*{re.escape(window_key)}.*"
    cur = conn.execute(
        "INSERT INTO windows (app_id, window_key, title_pattern, display_name) VALUES (?, ?, ?, ?)",
        (aid, window_key, pattern, window_key),
    )
    return int(cur.lastrowid)


def _row_to_object_dict(row: sqlite3.Row, conn: sqlite3.Connection) -> dict:
    oid = int(row["id"])
    ident = conn.execute(
        "SELECT mandatory, assistive, smart, ordinal FROM object_identification WHERE object_id=?",
        (oid,),
    ).fetchone()
    props = conn.execute(
        "SELECT full_properties FROM object_properties WHERE object_id=?",
        (oid,),
    ).fetchone()
    snap = conn.execute(
        "SELECT latest FROM object_snapshots WHERE object_id=?",
        (oid,),
    ).fetchone()
    res = conn.execute(
        "SELECT layer, backend, method, bbox, success_count, last_success "
        "FROM object_resolution WHERE object_id=?",
        (oid,),
    ).fetchone()
    hint = conn.execute(
        "SELECT hints FROM agent_hints WHERE scope='object' AND scope_id=?",
        (str(oid),),
    ).fetchone()

    identification = {
        "mandatory": _json_loads(ident["mandatory"] if ident else None),
        "assistive": _json_loads(ident["assistive"] if ident else None),
        "smart": _json_loads(ident["smart"] if ident else None),
        "ordinal": _json_loads(ident["ordinal"] if ident else None),
    }
    obj: dict[str, Any] = {
        "class": row["swf_class"],
        "parent": row["parent_key"],
        "identification": identification,
        "repo_path": row["repo_path"],
        "logical_name": row["logical_name"],
        "automation_id": row["automation_id"],
        "_window_key": conn.execute(
            "SELECT window_key FROM windows WHERE id=?", (row["window_id"],)
        ).fetchone()["window_key"],
        "_object_name": row["object_key"],
    }
    if props:
        fp = _json_loads(props["full_properties"])
        if fp:
            obj["full_properties"] = fp
    if snap:
        latest = _json_loads(snap["latest"])
        if latest:
            obj["snapshots"] = {"latest": _normalize_snapshot(latest)}
    if res:
        lr = {
            "layer": res["layer"] or "",
            "backend": res["backend"] or "",
            "method": res["method"] or "",
            "bbox": _json_loads(res["bbox"]),
            "success_count": res["success_count"] or 0,
            "last_success": res["last_success"] or "",
        }
        obj["last_resolution"] = lr
    if hint and hint["hints"]:
        obj["agent_hints"] = hint["hints"]
    return obj


def get_object_by_path(repo_path: str, db_path: Optional[Path] = None) -> Optional[dict]:
    _ensure_migrated(db_path)
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM objects WHERE repo_path=?", (repo_path,)).fetchone()
        if not row:
            return None
        window_key, chain = parse_repo_path(repo_path)
        if len(chain) > 1:
            expected_parent = chain[-2]
            if row["parent_key"] and row["parent_key"] != expected_parent:
                return None
        return _row_to_object_dict(row, conn)


def parse_repo_path(repo_path: str) -> tuple[str, list[str]]:
    parts = [p for p in repo_path.strip("/").split("/") if p]
    if len(parts) < 2:
        raise ValueError("repo_path must be 'windowKey/objectName' or nested path")
    return parts[0], parts[1:]


def upsert(
    app_name: str,
    exe_path: str,
    repo_path: str,
    *,
    obj_class: str = "control",
    identification: dict | None = None,
    last_resolution: dict | None = None,
    snapshots: dict | None = None,
    parent: str = "",
    element: dict | None = None,
    full_properties: dict | None = None,
    agent_hints: Optional[str] = None,
    framework: str = "unknown",
    app_id_value: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> dict:
    from detection.winforms_map import build_identification, infer_swf_class

    _ensure_migrated(db_path)
    aid = app_id_value or app_id(app_name, exe_path)
    window_key, chain = parse_repo_path(repo_path)
    object_key = chain[-1]
    if not parent and len(chain) > 1:
        parent = chain[-2]

    if element and obj_class == "control":
        obj_class = infer_swf_class(
            element.get("role", ""),
            element.get("class_name", ""),
            obj_class,
        )
    if element and not identification:
        identification = build_identification(element, obj_class)
    if element and not full_properties:
        full_properties = dict(element)

    automation_id_val = ""
    if element:
        automation_id_val = element.get("automation_id", "") or ""
    elif identification:
        automation_id_val = identification.get("mandatory", {}).get("automation_id", "")

    logical_name = object_key
    if element and element.get("name"):
        logical_name = element["name"]

    now = _now()
    ident = identification or {
        "mandatory": {},
        "assistive": {},
        "smart": {},
        "ordinal": {},
    }

    with _connect(db_path) as conn:
        _ensure_application(conn, aid, app_name, exe_path, framework)

        for i, pname in enumerate(chain[:-1]):
            pparent = chain[i - 1] if i > 0 else ""
            p_path = f"{window_key}/{'/'.join(chain[: i + 1])}"
            if not conn.execute("SELECT id FROM objects WHERE repo_path=?", (p_path,)).fetchone():
                wid = _ensure_window(conn, aid, window_key)
                conn.execute(
                    "INSERT INTO objects (window_id, repo_path, logical_name, object_key, parent_key, "
                    "swf_class, automation_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        wid,
                        p_path,
                        pname,
                        pname,
                        pparent,
                        "SwfPage" if i > 0 else "SwfTab",
                        "",
                        now,
                        now,
                    ),
                )
                pid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
                conn.execute(
                    "INSERT INTO object_identification (object_id, mandatory, assistive) VALUES (?, ?, ?)",
                    (
                        pid,
                        _json_dumps({"name": pname}),
                        _json_dumps({"role": "TabItem" if i > 0 else "Tab"}),
                    ),
                )

        wid = _ensure_window(conn, aid, window_key)
        existing = conn.execute("SELECT id FROM objects WHERE repo_path=?", (repo_path,)).fetchone()

        if existing:
            oid = int(existing["id"])
            conn.execute(
                "UPDATE objects SET logical_name=?, object_key=?, parent_key=?, swf_class=?, "
                "automation_id=?, updated_at=? WHERE id=?",
                (logical_name, object_key, parent, obj_class, automation_id_val, now, oid),
            )
        else:
            cur = conn.execute(
                "INSERT INTO objects (window_id, repo_path, logical_name, object_key, parent_key, "
                "swf_class, automation_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    wid,
                    repo_path,
                    logical_name,
                    object_key,
                    parent,
                    obj_class,
                    automation_id_val,
                    now,
                    now,
                ),
            )
            oid = int(cur.lastrowid)

        conn.execute(
            "INSERT INTO object_identification (object_id, mandatory, assistive, smart, ordinal) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(object_id) DO UPDATE SET "
            "mandatory=excluded.mandatory, assistive=excluded.assistive, "
            "smart=excluded.smart, ordinal=excluded.ordinal",
            (
                oid,
                _json_dumps(ident.get("mandatory", {})),
                _json_dumps(ident.get("assistive", {})),
                _json_dumps(ident.get("smart", {})),
                _json_dumps(ident.get("ordinal", {})),
            ),
        )

        if full_properties:
            conn.execute(
                "INSERT INTO object_properties (object_id, full_properties) VALUES (?, ?) "
                "ON CONFLICT(object_id) DO UPDATE SET full_properties=excluded.full_properties",
                (oid, _json_dumps(full_properties)),
            )

        if snapshots:
            conn.execute(
                "INSERT INTO object_snapshots (object_id, latest) VALUES (?, ?) "
                "ON CONFLICT(object_id) DO UPDATE SET latest=excluded.latest",
                (oid, _json_dumps(snapshots.get("latest", snapshots))),
            )

        if last_resolution:
            prev = conn.execute(
                "SELECT success_count FROM object_resolution WHERE object_id=?", (oid,)
            ).fetchone()
            sc = (prev["success_count"] if prev else 0) + 1
            conn.execute(
                "INSERT INTO object_resolution "
                "(object_id, layer, backend, method, bbox, success_count, last_success) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(object_id) DO UPDATE SET "
                "layer=excluded.layer, backend=excluded.backend, method=excluded.method, "
                "bbox=excluded.bbox, success_count=excluded.success_count, last_success=excluded.last_success",
                (
                    oid,
                    last_resolution.get("layer", ""),
                    last_resolution.get("backend", ""),
                    last_resolution.get("method", ""),
                    _json_dumps(last_resolution.get("bbox", {})),
                    sc,
                    now,
                ),
            )

        if agent_hints is not None:
            conn.execute(
                "INSERT INTO agent_hints (scope, scope_id, hints, updated_at) VALUES ('object', ?, ?, ?) "
                "ON CONFLICT(scope, scope_id) DO UPDATE SET hints=excluded.hints, updated_at=excluded.updated_at",
                (str(oid), agent_hints, now),
            )

        row = conn.execute("SELECT * FROM objects WHERE id=?", (oid,)).fetchone()
        return _row_to_object_dict(row, conn)


def list_objects_for_app(
    app_name: str,
    exe_path: str = "",
    window_key: str | None = None,
    db_path: Optional[Path] = None,
) -> list[dict]:
    _ensure_migrated(db_path)
    with _connect(db_path) as conn:
        aid = _resolve_lookup_app_id(app_name, exe_path, conn=conn)
        if window_key:
            rows = conn.execute(
                "SELECT o.* FROM objects o "
                "JOIN windows w ON o.window_id=w.id "
                "WHERE w.app_id=? AND w.window_key=?",
                (aid, window_key),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT o.* FROM objects o "
                "JOIN windows w ON o.window_id=w.id WHERE w.app_id=?",
                (aid,),
            ).fetchall()
        return [_row_to_object_dict(r, conn) for r in rows]


def load_repo_dict(app_name: str, exe_path: str = "", db_path: Optional[Path] = None) -> dict:
    """Build legacy in-memory repo dict for callers that still expect it."""
    _ensure_migrated(db_path)
    with _connect(db_path) as conn:
        aid = _resolve_lookup_app_id(app_name, exe_path, conn=conn)
        app = conn.execute("SELECT * FROM applications WHERE app_id=?", (aid,)).fetchone()
        if not app:
            return {
                "app_id": aid,
                "app_name": app_name,
                "framework": "unknown",
                "windows": {},
            }
        repo: dict[str, Any] = {
            "app_id": aid,
            "app_name": app["app_name"],
            "exe_path": app["exe_path"] or "",
            "framework": app["framework"],
            "windows": {},
        }
        windows = conn.execute("SELECT * FROM windows WHERE app_id=?", (aid,)).fetchall()
        for win in windows:
            wk = win["window_key"]
            repo["windows"][wk] = {
                "title_pattern": win["title_pattern"],
                "objects": {},
            }
            objs = conn.execute(
                "SELECT * FROM objects WHERE window_id=?", (win["id"],)
            ).fetchall()
            for row in objs:
                obj = _row_to_object_dict(row, conn)
                key = row["object_key"]
                repo["windows"][wk]["objects"][key] = {
                    k: v for k, v in obj.items()
                    if k not in ("repo_path", "_window_key", "_object_name", "logical_name", "automation_id")
                }
        return repo


def get_repo_revision(db_path: Optional[Path] = None) -> dict[str, Any]:
    """Lightweight fingerprint for polling — detects adds/updates/deletes."""
    _ensure_migrated(db_path)
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT "
            "(SELECT COUNT(*) FROM applications) AS app_count, "
            "(SELECT COUNT(*) FROM objects) AS object_count, "
            "(SELECT COALESCE(MAX(updated_at), '') FROM applications) AS apps_updated, "
            "(SELECT COALESCE(MAX(updated_at), '') FROM objects) AS objects_updated"
        ).fetchone()
        parts = (
            str(row["app_count"]),
            str(row["object_count"]),
            row["apps_updated"] or "",
            row["objects_updated"] or "",
        )
        return {
            "revision": ":".join(parts),
            "app_count": int(row["app_count"]),
            "object_count": int(row["object_count"]),
        }


def list_applications(db_path: Optional[Path] = None) -> list[dict]:
    _ensure_migrated(db_path)
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT a.app_id, a.app_name, a.exe_path, a.framework, a.agent_hints, "
            "a.created_at, a.updated_at, COUNT(o.id) AS object_count "
            "FROM applications a "
            "LEFT JOIN windows w ON w.app_id = a.app_id "
            "LEFT JOIN objects o ON o.window_id = w.id "
            "GROUP BY a.app_id "
            "ORDER BY a.app_name"
        ).fetchall()
        apps = []
        for r in rows:
            d = dict(r)
            d["object_count"] = int(d.get("object_count") or 0)
            apps.append(d)

    def sort_key(app: dict) -> tuple:
        from detection.repo_consolidate import is_junk_app_name

        junk = is_junk_app_name(app.get("app_name", ""))
        return (junk, -int(app.get("object_count") or 0), (app.get("app_name") or "").lower())

    apps.sort(key=sort_key)
    return apps


def get_app_tree(app_id_value: str, db_path: Optional[Path] = None) -> dict:
    _ensure_migrated(db_path)
    with _connect(db_path) as conn:
        app = conn.execute("SELECT * FROM applications WHERE app_id=?", (app_id_value,)).fetchone()
        if not app:
            return {"error": "app not found"}
        windows_out = []
        for win in conn.execute("SELECT * FROM windows WHERE app_id=? ORDER BY window_key", (app_id_value,)):
            objs = []
            for row in conn.execute(
                "SELECT repo_path, logical_name, swf_class, object_key, parent_key, automation_id "
                "FROM objects WHERE window_id=? ORDER BY repo_path",
                (win["id"],),
            ):
                objs.append(dict(row))
            if not objs:
                continue
            windows_out.append({
                "window_key": win["window_key"],
                "title_pattern": win["title_pattern"],
                "display_name": win["display_name"],
                "objects": objs,
            })
        return {
            "app_id": app["app_id"],
            "app_name": app["app_name"],
            "framework": app["framework"],
            "windows": windows_out,
        }


def search_objects(q: str, db_path: Optional[Path] = None) -> list[dict]:
    _ensure_migrated(db_path)
    like = f"%{q}%"
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT o.* FROM objects o "
            "WHERE o.repo_path LIKE ? OR o.logical_name LIKE ? OR o.automation_id LIKE ? "
            "ORDER BY o.repo_path LIMIT 100",
            (like, like, like),
        ).fetchall()
        return [_row_to_object_dict(r, conn) for r in rows]


def update_object(
    repo_path: str,
    *,
    logical_name: Optional[str] = None,
    identification: Optional[dict] = None,
    agent_hints: Optional[str] = None,
    full_properties: Optional[dict] = None,
    db_path: Optional[Path] = None,
) -> Optional[dict]:
    _ensure_migrated(db_path)
    with _connect(db_path) as conn:
        row = conn.execute("SELECT id FROM objects WHERE repo_path=?", (repo_path,)).fetchone()
        if not row:
            return None
        oid = int(row["id"])
        now = _now()
        if logical_name:
            conn.execute(
                "UPDATE objects SET logical_name=?, updated_at=? WHERE id=?",
                (logical_name, now, oid),
            )
        if identification:
            conn.execute(
                "UPDATE object_identification SET mandatory=?, assistive=?, smart=?, ordinal=? "
                "WHERE object_id=?",
                (
                    _json_dumps(identification.get("mandatory", {})),
                    _json_dumps(identification.get("assistive", {})),
                    _json_dumps(identification.get("smart", {})),
                    _json_dumps(identification.get("ordinal", {})),
                    oid,
                ),
            )
        if full_properties is not None:
            conn.execute(
                "INSERT INTO object_properties (object_id, full_properties) VALUES (?, ?) "
                "ON CONFLICT(object_id) DO UPDATE SET full_properties=excluded.full_properties",
                (oid, _json_dumps(full_properties)),
            )
        if agent_hints is not None:
            conn.execute(
                "INSERT INTO agent_hints (scope, scope_id, hints, updated_at) VALUES ('object', ?, ?, ?) "
                "ON CONFLICT(scope, scope_id) DO UPDATE SET hints=excluded.hints, updated_at=excluded.updated_at",
                (str(oid), agent_hints, now),
            )
        row2 = conn.execute("SELECT * FROM objects WHERE id=?", (oid,)).fetchone()
        return _row_to_object_dict(row2, conn)


def delete_object(repo_path: str, db_path: Optional[Path] = None) -> bool:
    _ensure_migrated(db_path)
    with _connect(db_path) as conn:
        cur = conn.execute("DELETE FROM objects WHERE repo_path=?", (repo_path,))
        return cur.rowcount > 0


def get_agent_hints(repo_path: str, db_path: Optional[Path] = None) -> str:
    _ensure_migrated(db_path)
    with _connect(db_path) as conn:
        row = conn.execute("SELECT id FROM objects WHERE repo_path=?", (repo_path,)).fetchone()
        if not row:
            return ""
        hint = conn.execute(
            "SELECT hints FROM agent_hints WHERE scope='object' AND scope_id=?",
            (str(row["id"]),),
        ).fetchone()
        return hint["hints"] if hint else ""


def migrate_json_repos(db_path: Optional[Path] = None, force: bool = False) -> dict:
    """Import legacy JSON repos into SQLite."""
    global _migrated, _migrating
    if _migrating:
        return {"imported": 0, "skipped": True, "reason": "in_progress"}
    if not _LEGACY_JSON_DIR.exists():
        return {"imported": 0, "skipped": True}

    if not force:
        with _connect(db_path) as conn:
            count = conn.execute("SELECT COUNT(*) AS c FROM objects").fetchone()["c"]
            if count > 0:
                _migrated = True
                return {"imported": 0, "skipped": True, "reason": "db_not_empty"}

    _migrating = True
    imported = 0
    try:
        json_files = list(_LEGACY_JSON_DIR.glob("*.json"))
        for jpath in json_files:
            try:
                data = json.loads(jpath.read_text(encoding="utf-8"))
            except Exception:
                continue
            aid = data.get("app_id", jpath.stem)
            app_name = data.get("app_name", aid)
            framework = data.get("framework", "unknown")

            old_assets = _LEGACY_JSON_DIR / aid / "assets"
            if old_assets.exists():
                dest = assets_dir(aid)
                for f in old_assets.glob("*"):
                    if f.is_file():
                        shutil.copy2(f, dest / f.name)

            for wk, wdata in data.get("windows", {}).items():
                objects = wdata.get("objects", {})
                for name, obj in objects.items():
                    chain: list[str] = []
                    current = name
                    seen: set[str] = set()
                    while current and current not in seen:
                        seen.add(current)
                        chain.insert(0, current)
                        current = objects.get(current, {}).get("parent", "") or ""
                    full_path = f"{wk}/{'/'.join(chain)}"
                    o = objects[name]
                    upsert(
                        app_name,
                        "",
                        full_path,
                        obj_class=o.get("class", "SwfObject"),
                        identification=o.get("identification"),
                        last_resolution=o.get("last_resolution"),
                        snapshots=o.get("snapshots"),
                        parent=o.get("parent", ""),
                        full_properties=o.get("full_properties")
                        or (o.get("snapshots", {}).get("latest", {}).get("full_properties")),
                        framework=framework,
                        app_id_value=aid,
                        db_path=db_path,
                    )
                    imported += 1

        _migrated = True
        real_legacy = _DATA_DIR / "repositories"
        if (
            imported > 0
            and _LEGACY_JSON_DIR.resolve() == real_legacy.resolve()
            and not _LEGACY_JSON_BAK.exists()
        ):
            try:
                shutil.move(str(_LEGACY_JSON_DIR), str(_LEGACY_JSON_BAK))
            except Exception:
                pass
    finally:
        _migrating = False

    return {"imported": imported, "skipped": False}


def reset_migration_flag() -> None:
    global _migrated, _migrating
    _migrated = False
    _migrating = False

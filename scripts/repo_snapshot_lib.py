"""Export repository snapshot for a lab run (objects + agent_hints)."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = REPO_ROOT / "mcp-servers" / "awdui-server"


def _parse_discovered_app(run_dir: Path) -> str | None:
    path = run_dir / "discovered.yaml"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8-sig")
    for line in text.splitlines():
        m = re.match(r"^\s*app_name:\s*(.+)\s*$", line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    return None


def _match_app(app_name: str, candidate: str) -> bool:
    a = app_name.lower().strip()
    c = candidate.lower().strip()
    if not a or not c:
        return False
    return a in c or c in a or a.split(".")[0] in c


def build_repo_snapshot(run_dir: Path) -> dict[str, Any] | None:
    """List repo objects + hints for app in discovered.yaml."""
    app_name = _parse_discovered_app(run_dir)
    if not app_name:
        return None

    if str(SERVER_ROOT) not in __import__("sys").path:
        import sys

        sys.path.insert(0, str(SERVER_ROOT))

    from detection import repo_store
    from detection.object_repository import list_objects, load_repo

    apps = repo_store.list_applications()
    target = None
    for app in apps:
        if _match_app(app_name, app.get("app_name") or ""):
            target = app
            break
    if not target:
        return {
            "app_name": app_name,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "object_count": 0,
            "objects_with_hints": 0,
            "objects": [],
            "note": "no matching application in repository.db",
        }

    repo = load_repo(target["app_name"], target.get("exe_path") or "")
    objs = list_objects(repo)
    rows: list[dict[str, Any]] = []
    with_hints = 0
    for obj in objs:
        path = obj.get("repo_path") or ""
        hints = repo_store.get_agent_hints(path) if path else ""
        if hints.strip():
            with_hints += 1
        ident = obj.get("identification") or {}
        mand = ident.get("mandatory") or {}
        rows.append(
            {
                "repo_path": path,
                "class": obj.get("class"),
                "automation_id": mand.get("automation_id") or obj.get("automation_id"),
                "name": (ident.get("assistive") or {}).get("name") or obj.get("name"),
                "agent_hints": hints,
                "has_hints": bool(hints.strip()),
            }
        )

    return {
        "app_name": app_name,
        "repo_app": target.get("app_name"),
        "app_id": target.get("app_id"),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "object_count": len(rows),
        "objects_with_hints": with_hints,
        "objects": rows,
    }


def write_repo_snapshot(run_dir: Path) -> Path | None:
    snapshot = build_repo_snapshot(run_dir)
    if snapshot is None:
        return None
    out = run_dir / "repo-snapshot.json"
    out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out

"""Merge duplicate / junk application buckets in the object repository."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from detection.repo_store import (
    _connect,
    _ensure_application,
    _ensure_migrated,
    _ensure_window,
    _now,
    app_id,
)

JUNK_APP_NAMES = frozenset(
    {
        "foreground",
        "unknown",
        "smoke",
        "applicationframehost.exe",
    }
)

WINDOW_APP_ALIASES: dict[str, tuple[str, str]] = {
    "calculadora": ("CalculatorApp.exe", ""),
    "calculator": ("CalculatorApp.exe", ""),
    "notepad": ("Notepad.exe", ""),
    "bloc_de_notas": ("Notepad.exe", ""),
}

APP_WINDOW_DISPLAY: dict[str, str] = {
    "CalculatorApp.exe": "Calculadora",
    "Notepad.exe": "Notepad",
}


def is_junk_app_name(app_name: str) -> bool:
    lower = (app_name or "").strip().lower()
    if not lower:
        return True
    if lower in JUNK_APP_NAMES:
        return True
    return lower.endswith("applicationframehost.exe")


def _normalize_window_key(window_key: str) -> str:
    return (window_key or "").strip().lower().replace("_", " ")


def _infer_from_text(*parts: str) -> Optional[tuple[str, str]]:
    blob = " ".join(p for p in parts if p).lower()
    if any(k in blob for k in ("notepad", "bloc de notas", "bloc_de_notas")):
        return WINDOW_APP_ALIASES["notepad"]
    if any(k in blob for k in ("calculadora", "calculator", "calc")):
        return WINDOW_APP_ALIASES["calculadora"]
    return None


def canonical_for_window(
    window_key: str,
    app_index: dict[str, dict],
    *,
    repo_path: str = "",
    logical_name: str = "",
) -> tuple[str, str]:
    """Pick the stable app bucket for objects under *window_key*."""
    inferred = _infer_from_text(window_key, repo_path, logical_name)
    if inferred:
        return inferred

    norm = _normalize_window_key(window_key)
    if norm in WINDOW_APP_ALIASES:
        return WINDOW_APP_ALIASES[norm]

    best: tuple[int, str, str] | None = None
    for info in app_index.values():
        if is_junk_app_name(info["app_name"]):
            continue
        count = int(info["windows"].get(window_key, 0))
        if count <= 0:
            continue
        candidate = (count, info["app_name"], info["exe_path"])
        if best is None or candidate[0] > best[0]:
            best = candidate
    if best:
        return best[1], best[2]

    display = (window_key or "main").replace("_", " ")
    return display, ""


def canonical_window_key(
    window_key: str,
    app_name: str,
    *,
    repo_path: str = "",
    logical_name: str = "",
) -> str:
    if app_name in APP_WINDOW_DISPLAY:
        return APP_WINDOW_DISPLAY[app_name]
    parts = [p for p in repo_path.split("/") if p]
    if parts and not is_junk_app_name(parts[0]):
        return parts[0]
    inferred = _infer_from_text(window_key, repo_path, logical_name)
    if inferred:
        for app, display in APP_WINDOW_DISPLAY.items():
            if inferred[0] == app:
                return display
    return window_key or "main"


def normalize_repo_path(repo_path: str, window_key: str) -> str:
    parts = [p for p in repo_path.split("/") if p]
    if not parts:
        return repo_path
    if parts[0] == window_key:
        return repo_path
    return "/".join([window_key, *parts[1:]])


def _object_quality(conn: sqlite3.Connection, oid: int) -> int:
    score = 0
    if conn.execute(
        "SELECT 1 FROM object_snapshots WHERE object_id=? AND latest != '{}'",
        (oid,),
    ).fetchone():
        score += 20
    if conn.execute(
        "SELECT 1 FROM object_properties WHERE object_id=? AND full_properties != '{}'",
        (oid,),
    ).fetchone():
        score += 10
    res = conn.execute(
        "SELECT success_count FROM object_resolution WHERE object_id=?", (oid,)
    ).fetchone()
    if res:
        score += int(res["success_count"] or 0) * 2
    return score


def _build_app_index(conn: sqlite3.Connection) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for app in conn.execute(
        "SELECT app_id, app_name, exe_path, framework FROM applications"
    ):
        aid = app["app_id"]
        windows: dict[str, int] = {}
        for row in conn.execute(
            "SELECT w.window_key, COUNT(o.id) AS cnt "
            "FROM windows w LEFT JOIN objects o ON o.window_id = w.id "
            "WHERE w.app_id=? GROUP BY w.window_key",
            (aid,),
        ):
            windows[row["window_key"]] = int(row["cnt"])
        index[aid] = {
            "app_id": aid,
            "app_name": app["app_name"],
            "exe_path": app["exe_path"] or "",
            "framework": app["framework"] or "unknown",
            "windows": windows,
            "object_count": sum(windows.values()),
        }
    return index


def _cleanup_empty(conn: sqlite3.Connection) -> tuple[int, int]:
    removed_windows = conn.execute(
        "DELETE FROM windows WHERE id NOT IN (SELECT DISTINCT window_id FROM objects)"
    ).rowcount
    removed_apps = conn.execute(
        "DELETE FROM applications WHERE app_id NOT IN (SELECT DISTINCT app_id FROM windows)"
    ).rowcount
    return removed_windows, removed_apps


def consolidate_repositories(db_path: Optional[Path] = None) -> dict:
    """Move objects out of junk/duplicate apps into canonical per-window buckets."""
    _ensure_migrated(db_path)
    moved = 0
    merged = 0
    removed_objects = 0
    removed_windows = 0
    removed_apps = 0

    with _connect(db_path) as conn:
        app_index = _build_app_index(conn)
        target_cache: dict[str, str] = {}

        def target_app_id(window_key: str, repo_path: str, logical_name: str) -> str:
            cache_key = f"{window_key}|{repo_path}|{logical_name}"
            if cache_key in target_cache:
                return target_cache[cache_key]
            name, exe = canonical_for_window(
                window_key, app_index, repo_path=repo_path, logical_name=logical_name
            )
            aid = app_id(name, exe)
            framework = "unknown"
            for info in app_index.values():
                if info["app_name"] == name and (info["exe_path"] or "") == (exe or ""):
                    framework = info.get("framework", "unknown")
                    break
            _ensure_application(conn, aid, name, exe, framework)
            target_cache[cache_key] = aid
            if aid not in app_index:
                app_index[aid] = {
                    "app_id": aid,
                    "app_name": name,
                    "exe_path": exe,
                    "framework": framework,
                    "windows": {},
                    "object_count": 0,
                }
            return aid

        rows = conn.execute(
            "SELECT o.id, o.repo_path, o.logical_name, w.window_key, w.app_id, a.app_name "
            "FROM objects o "
            "JOIN windows w ON w.id = o.window_id "
            "JOIN applications a ON a.app_id = w.app_id "
            "ORDER BY o.repo_path"
        ).fetchall()

        for row in rows:
            oid = int(row["id"])
            window_key = row["window_key"]
            source_app_id = row["app_id"]
            source_app_name = row["app_name"]
            repo_path = row["repo_path"]
            logical_name = row["logical_name"] or ""

            target_aid = target_app_id(window_key, repo_path, logical_name)
            if source_app_id == target_aid and not is_junk_app_name(source_app_name):
                continue

            target_app_name = app_index.get(target_aid, {}).get("app_name") or canonical_for_window(
                window_key, app_index, repo_path=repo_path, logical_name=logical_name
            )[0]
            display_window = canonical_window_key(
                window_key, target_app_name, repo_path=repo_path, logical_name=logical_name
            )
            new_repo_path = normalize_repo_path(repo_path, display_window)
            target_wid = _ensure_window(conn, target_aid, display_window)
            dup = conn.execute(
                "SELECT o.id FROM objects o "
                "JOIN windows w ON w.id = o.window_id "
                "WHERE o.repo_path=? AND w.app_id=? AND o.id != ?",
                (new_repo_path, target_aid, oid),
            ).fetchone()

            if dup:
                other_id = int(dup["id"])
                if _object_quality(conn, oid) >= _object_quality(conn, other_id):
                    conn.execute("DELETE FROM objects WHERE id=?", (other_id,))
                    conn.execute(
                        "UPDATE objects SET window_id=?, repo_path=?, updated_at=? WHERE id=?",
                        (target_wid, new_repo_path, _now(), oid),
                    )
                    moved += 1
                else:
                    conn.execute("DELETE FROM objects WHERE id=?", (oid,))
                removed_objects += 1
                merged += 1
            else:
                conn.execute(
                    "UPDATE objects SET window_id=?, repo_path=?, updated_at=? WHERE id=?",
                    (target_wid, new_repo_path, _now(), oid),
                )
                moved += 1

        rw, ra = _cleanup_empty(conn)
        removed_windows += rw
        removed_apps += ra

        from detection.repo_store import list_applications

        apps = list_applications(db_path)

    return {
        "moved": moved,
        "merged": merged,
        "removed_objects": removed_objects,
        "removed_windows": removed_windows,
        "removed_apps": removed_apps,
        "apps": apps,
    }

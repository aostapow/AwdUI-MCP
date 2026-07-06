"""UFT-style object repository — facade over SQLite store."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

from detection import repo_store
from detection.winforms_map import build_identification, infer_swf_class

# Re-export for compatibility
app_id = repo_store.app_id
parse_repo_path = repo_store.parse_repo_path


def _app_id(app_name: str, exe_path: str = "") -> str:
    return repo_store.app_id(app_name, exe_path)


def load_repo(app_name: str, exe_path: str = "") -> dict:
    return repo_store.load_repo_dict(app_name, exe_path)


def save_repo(repo: dict) -> None:
    """No-op for SQLite backend; kept for API compatibility."""
    pass


def get_object(repo: dict, repo_path: str) -> Optional[dict]:
    obj = repo_store.get_object_by_path(repo_path)
    if obj:
        return obj
    # Fallback: search in provided in-memory repo dict (tests)
    try:
        window_key, chain = parse_repo_path(repo_path)
    except ValueError:
        return None
    win = repo.get("windows", {}).get(window_key)
    if not win:
        return None
    objects = win.get("objects", {})
    leaf_name = chain[-1]
    raw = objects.get(leaf_name)
    if not raw:
        return None
    if len(chain) > 1:
        expected_parent = chain[-2]
        stored_parent = raw.get("parent", "")
        if stored_parent and stored_parent != expected_parent:
            return None
    out = dict(raw)
    out["repo_path"] = repo_path
    out["_window_key"] = window_key
    out["_object_name"] = chain[-1]
    return out


def upsert_object(
    repo: dict,
    repo_path: str,
    *,
    obj_class: str = "control",
    identification: dict | None = None,
    last_resolution: dict | None = None,
    snapshots: dict | None = None,
    parent: str = "",
    element: dict | None = None,
    agent_hints: Optional[str] = None,
) -> dict:
    app_name = repo.get("app_name", "foreground")
    exe_path = repo.get("exe_path", "")
    framework = repo.get("framework", "unknown")
    full_properties = None
    if element:
        full_properties = dict(element)
    return repo_store.upsert(
        app_name,
        exe_path,
        repo_path,
        obj_class=obj_class,
        identification=identification,
        last_resolution=last_resolution,
        snapshots=snapshots,
        parent=parent,
        element=element,
        full_properties=full_properties,
        agent_hints=agent_hints,
        framework=framework,
        app_id_value=repo.get("app_id"),
    )


def list_objects(repo: dict, window_key: str | None = None) -> list[dict]:
    app_name = repo.get("app_name", "foreground")
    exe_path = repo.get("exe_path", "")
    if repo.get("windows"):
        result = []
        windows = repo.get("windows", {})
        targets = {window_key: windows[window_key]} if window_key and window_key in windows else windows
        for wk, wdata in targets.items():
            objects = wdata.get("objects", {})
            for name in objects:
                full = _build_full_path(objects, name, wk)
                obj = dict(objects[name])
                result.append({"repo_path": full, **obj})
        if result:
            return result
    return repo_store.list_objects_for_app(app_name, exe_path, window_key)


def _build_full_path(objects: dict, name: str, window_key: str) -> str:
    chain: list[str] = []
    current: str = name
    seen: set[str] = set()
    while current and current not in seen:
        seen.add(current)
        chain.insert(0, current)
        current = objects.get(current, {}).get("parent", "") or ""
    return f"{window_key}/{'/'.join(chain)}"


def assets_path(app_id_value: str, filename: str) -> Path:
    return repo_store.assets_path(app_id_value, filename)


def relative_asset(app_id_value: str, filename: str) -> str:
    return repo_store.relative_asset(app_id_value, filename)


def ensure_repo(app_name: str, exe_path: str = "", framework: str = "unknown") -> dict:
    """Load or create repo context dict for upsert operations."""
    repo = load_repo(app_name, exe_path)
    repo["exe_path"] = exe_path
    repo["framework"] = framework
    return repo

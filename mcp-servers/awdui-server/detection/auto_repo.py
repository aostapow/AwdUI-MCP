"""Auto-remember successful element resolutions in the object repository."""
from __future__ import annotations

import re
from typing import Any, Optional

from detection.object_repository import load_repo, upsert_object
from detection.winforms_map import build_identification, infer_swf_class
from detection.app_identity import repository_app_name, title_app_name


def _window_key(window_title: Optional[str]) -> str:
    raw = (window_title or "main").strip()
    if not raw:
        return "main"
    token = raw.split(" - ")[0].split("|")[0].strip()
    safe = re.sub(r"[^\w\-]", "_", token)
    return (safe or "main")[:48]


def _object_key(elem: dict) -> str:
    aid = (elem.get("automation_id") or "").strip()
    if aid:
        return re.sub(r"[^\w\-]", "_", aid)[:64]
    name = (elem.get("name") or "").strip()
    if name:
        return re.sub(r"[^\w\-]", "_", name)[:64]
    role = (elem.get("role") or "control").replace("ControlType.", "")
    x, y = elem.get("x", 0), elem.get("y", 0)
    return f"{role}_{x}_{y}"[:64]


def auto_repo_path(window_title: Optional[str], elem: dict) -> str:
    return f"{_window_key(window_title)}/{_object_key(elem)}"


def maybe_remember_element(
    elem: dict,
    *,
    window_title: Optional[str] = None,
    repo_path: Optional[str] = None,
    backend: str = "uia",
    remember: bool = True,
) -> Optional[str]:
    """Upsert *elem* into the repo. Returns the repo_path used, or None."""
    if not remember or not elem:
        return None
    path = repo_path or auto_repo_path(window_title, elem)
    try:
        from tools.framework_detect import do_detect_framework
        fw = do_detect_framework(window_title)
        app_name, exe_path = repository_app_name(fw, window_title)
    except Exception:
        app_name = title_app_name(window_title) or "unknown"
        exe_path = ""

    repo = load_repo(app_name, exe_path)
    repo["exe_path"] = exe_path
    swf = infer_swf_class(elem.get("role", ""), elem.get("class_name", ""))
    normalized = elem
    try:
        from detection.element_coords import to_screen_coords

        normalized = to_screen_coords(dict(elem), window_title)
    except Exception:
        pass
    snapshots = None
    try:
        from detection.object_snapshot import capture_element_crop

        snapshots = capture_element_crop(
            normalized, repo_path=path, app_id=repo["app_id"], window_title=window_title
        )
    except Exception:
        pass
    upsert_object(
        repo,
        path,
        obj_class=swf,
        element=normalized,
        identification=build_identification(normalized, swf),
        snapshots=snapshots,
        last_resolution={
            "layer": "native",
            "backend": backend,
            "bbox": {
                "x": normalized.get("x", 0),
                "y": normalized.get("y", 0),
                "w": normalized.get("width", 0),
                "h": normalized.get("height", 0),
            },
        },
    )
    return path

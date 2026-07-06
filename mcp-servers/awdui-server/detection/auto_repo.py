"""Auto-remember successful element resolutions in the object repository."""
from __future__ import annotations

import re
from typing import Any, Optional

from detection.object_repository import load_repo, upsert_object
from detection.winforms_map import build_identification, infer_swf_class


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
        app_name = fw.get("process_name") or fw.get("exe_name") or "foreground"
        exe_path = fw.get("exe_path", "")
    except Exception:
        app_name, exe_path = "foreground", ""

    repo = load_repo(app_name, exe_path)
    repo["exe_path"] = exe_path
    swf = infer_swf_class(elem.get("role", ""), elem.get("class_name", ""))
    snapshots = None
    try:
        from detection.object_snapshot import capture_element_crop

        snapshots = capture_element_crop(
            elem, repo_path=path, app_id=repo["app_id"], window_title=window_title
        )
    except Exception:
        pass
    upsert_object(
        repo,
        path,
        obj_class=swf,
        element=elem,
        identification=build_identification(elem, swf),
        snapshots=snapshots,
        last_resolution={
            "layer": "native",
            "backend": backend,
            "bbox": {
                "x": elem.get("x", 0),
                "y": elem.get("y", 0),
                "w": elem.get("width", 0),
                "h": elem.get("height", 0),
            },
        },
    )
    return path

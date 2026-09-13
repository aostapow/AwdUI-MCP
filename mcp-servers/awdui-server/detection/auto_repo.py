"""Auto-remember successful element resolutions in the object repository."""
from __future__ import annotations

import os
import re
from typing import Any, Optional

from detection.object_repository import load_repo, upsert_object
from detection.winforms_map import build_identification, infer_swf_class
from detection.app_identity import repository_app_name, title_app_name

# Auto-capture exclusions only (explicit ``repo_capture`` is always allowed).
#
# Default: every app under ``set_target_window`` persists on successful interaction.
# Excluded executables are agent hosts, IDEs, and OS input chrome — never automation targets.
#
# | exe | Reason |
# |-----|--------|
# | cursor.exe, code.exe, devenv.exe | IDE / agent host |
# | node.exe, python.exe | MCP / script runtime |
# | cmd.exe, powershell.exe, wt.exe, windowsterminal.exe | Shells |
# | microsoft.cmdpal.ui.exe, powertoys.quickaccess.exe | OS launcher overlays |
# | textinputhost.exe | Windows touch keyboard |
AUTO_REPO_EXCLUDED_EXECUTABLES = frozenset({
    "cmd.exe",
    "code.exe",
    "cursor.exe",
    "devenv.exe",
    "microsoft.cmdpal.ui.exe",
    "node.exe",
    "powershell.exe",
    "powertoys.quickaccess.exe",
    "python.exe",
    "textinputhost.exe",
    "windowsterminal.exe",
    "wt.exe",
})

# Back-compat alias (tests / older docs).
HOST_REPO_BLOCKLIST = AUTO_REPO_EXCLUDED_EXECUTABLES


def _env_auto_repo_without_target() -> bool:
    return os.environ.get("AWDUI_AUTO_REPO", "").strip().lower() in ("1", "true", "yes")


def _normalize_exe_base(name: str) -> str:
    base = (name or "").lower().strip()
    if "\\" in base:
        base = base.rsplit("\\", 1)[-1]
    return base


def is_blocked_repo_app(app_name: str, exe_path: str = "") -> bool:
    """True only for AUTO_REPO_EXCLUDED_EXECUTABLES (see module doc above)."""
    for candidate in (app_name, exe_path):
        base = _normalize_exe_base(candidate)
        if base and base in HOST_REPO_BLOCKLIST:
            return True
    return False


def _window_matches_target(window_title: Optional[str], target: Optional[str]) -> bool:
    if not target:
        return False
    wt = (window_title or "").strip().lower()
    tg = target.strip().lower()
    if not wt or not tg:
        return False
    wt_head = wt.split(" - ")[0].split("|")[0].strip()
    tg_head = tg.split(" - ")[0].split("|")[0].strip()
    return (
        tg in wt
        or wt in tg
        or tg_head in wt
        or wt_head in tg
        or tg in wt_head
        or wt_head in tg_head
    )


def should_auto_remember(
    window_title: Optional[str],
    app_name: str = "",
    exe_path: str = "",
    *,
    force: bool = False,
) -> bool:
    """Gate auto-capture: only the active ``set_target_window`` app, unless forced."""
    if force:
        return True
    if is_blocked_repo_app(app_name, exe_path):
        return False
    try:
        from tools.target_window import get_target

        target = get_target()
    except Exception:
        target = None
    if target:
        # Actions scoped via set_target_window often pass window_title=None; target gate is enough.
        if not (window_title or "").strip():
            return True
        return _window_matches_target(window_title, target)
    return _env_auto_repo_without_target()


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


def remember_successful_act(
    result: dict,
    *,
    window_title: Optional[str] = None,
    repo_path: Optional[str] = None,
    backend: str = "uia",
) -> Optional[str]:
    """Upsert the acted element after a successful click/invoke/expand (idempotent upsert)."""
    if not result.get("success"):
        return None
    elem = result.get("element")
    if not elem or not isinstance(elem, dict):
        return None
    if not (window_title or "").strip():
        try:
            from tools.target_window import get_target

            window_title = get_target()
        except Exception:
            pass
    return maybe_remember_element(
        elem,
        window_title=window_title,
        repo_path=repo_path or result.get("repo_path"),
        backend=result.get("backend_used") or backend,
        remember=True,
    )


def maybe_remember_element(
    elem: dict,
    *,
    window_title: Optional[str] = None,
    repo_path: Optional[str] = None,
    backend: str = "uia",
    remember: bool = True,
    force: bool = False,
) -> Optional[str]:
    """Upsert *elem* into the repo. Returns the repo_path used, or None."""
    if not remember or not elem:
        return None
    app_guess = title_app_name(window_title) or "unknown"
    if not should_auto_remember(window_title, app_guess, "", force=force):
        return None
    try:
        from tools.framework_detect import do_detect_framework
        fw = do_detect_framework(window_title)
        app_name, exe_path = repository_app_name(fw, window_title)
        fw_label = fw.get("framework", "unknown")
    except Exception:
        app_name = app_guess
        exe_path = ""
        fw_label = "unknown"
    if is_blocked_repo_app(app_name, exe_path):
        return None

    path = repo_path or auto_repo_path(window_title, elem)
    repo = load_repo(app_name, exe_path)
    repo["exe_path"] = exe_path
    try:
        from detection.repo_framework import merge_framework

        repo["framework"] = merge_framework(repo.get("framework", "unknown"), fw_label)
    except Exception:
        repo["framework"] = fw_label
    swf = infer_swf_class(elem.get("role", ""), elem.get("class_name", ""))
    normalized = elem
    try:
        from detection.element_coords import to_screen_coords

        normalized = to_screen_coords(dict(elem), window_title)
    except Exception:
        pass
    snapshots = None
    try:
        from tools.perf import remember_snapshots

        if remember_snapshots():
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

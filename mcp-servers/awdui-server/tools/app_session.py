"""app_id session registry (shared across tools)."""
from __future__ import annotations

import uuid
from typing import Any, Optional

# app_id -> {pid, hwnd, title, process_name}
_apps: dict[str, dict[str, Any]] = {}


def normalize_index(index: int) -> int:
    """Treat index -1 as first match (legacy convention)."""
    if index < 0:
        return 0
    return index


def pick_element_index(index: int, count: int) -> int:
    if count <= 0:
        return 0
    return min(normalize_index(index), count - 1)


def _next_app_id() -> str:
    return f"app_{uuid.uuid4().hex[:8]}"


def get_app(app_id: str) -> Optional[dict[str, Any]]:
    if not app_id:
        return None
    return _apps.get(app_id)


def list_registered_apps() -> dict[str, dict[str, Any]]:
    return dict(_apps)


def unregister_app(app_id: str) -> Optional[dict[str, Any]]:
    return _apps.pop(app_id, None)


def clear_apps() -> None:
    _apps.clear()


def register_window(win: dict[str, Any], *, set_target: bool = True) -> dict[str, Any]:
    """Register a top-level window and return session metadata including app_id."""
    app_id = _next_app_id()
    entry = {
        "pid": int(win.get("pid") or win.get("process_id") or 0),
        "hwnd": int(win.get("hwnd") or 0),
        "title": str(win.get("title") or ""),
        "process_name": str(win.get("process") or win.get("process_name") or ""),
    }
    _apps[app_id] = entry
    if set_target and entry["title"]:
        from tools.target_window import set_target

        set_target(entry["title"])
    return {"success": True, "app_id": app_id, **entry}


def register_launch(
    *,
    pid: int = 0,
    hwnd: int = 0,
    title: str = "",
    process_name: str = "",
    set_target: bool = True,
) -> dict[str, Any]:
    """Register app session after launch_app / reuse."""
    if pid or hwnd or title:
        return register_window(
            {
                "pid": pid,
                "hwnd": hwnd,
                "title": title,
                "process": process_name,
            },
            set_target=set_target,
        )
    return {"success": False, "error": "cannot register empty launch session"}


def resolve_scope(
    app_id: str = "",
    window_title: Optional[str] = None,
    window_handle: Optional[int] = None,
) -> tuple[Optional[str], Optional[int], Optional[dict[str, Any]]]:
    """Resolve window title/hwnd from app_id. Third value is error dict if app_id unknown."""
    wt = (window_title or "").strip() or None
    hwnd = int(window_handle or 0) or None
    if app_id:
        app = _apps.get(app_id)
        if not app:
            return wt, hwnd, {"success": False, "error": f"Unknown app_id: {app_id}"}
        if not wt:
            wt = str(app.get("title") or app.get("process_name") or "") or None
        if not hwnd:
            hwnd = int(app.get("hwnd") or 0) or None
    return wt, hwnd, None


def apply_scope_to_launch_result(result: dict[str, Any], path: str) -> dict[str, Any]:
    """Attach app_id to a successful launch_app / reuse result."""
    if not result.get("success"):
        return result
    pid = int(result.get("pid") or 0)
    title = str(result.get("window_title") or "")
    hwnd = 0
    if pid or title:
        try:
            from tools.windows import do_list_windows

            for win in do_list_windows():
                if pid and int(win.get("pid") or 0) == pid:
                    hwnd = int(win.get("hwnd") or 0)
                    if not title:
                        title = str(win.get("title") or "")
                    break
                if title and title.lower() in str(win.get("title") or "").lower():
                    hwnd = int(win.get("hwnd") or 0)
                    pid = int(win.get("pid") or 0) or pid
                    break
        except Exception:
            pass
    reg = register_launch(
        pid=pid,
        hwnd=hwnd,
        title=title,
        process_name=path,
        set_target=not title,
    )
    if reg.get("app_id"):
        result["app_id"] = reg["app_id"]
    return result


def filter_windows_for_app(
    windows: list[dict[str, Any]],
    app_id: str = "",
) -> list[dict[str, Any]]:
    if not app_id:
        return windows
    app = _apps.get(app_id)
    if not app:
        return []
    pid = int(app.get("pid") or 0)
    if not pid:
        return []
    return [w for w in windows if int(w.get("pid") or w.get("process_id") or 0) == pid]

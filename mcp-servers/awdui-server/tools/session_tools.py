"""Session health and cleanup helpers for long GUI automation runs."""
from __future__ import annotations

import sys
from typing import Any, Optional


def _workstation_locked() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import ctypes

        user32 = ctypes.windll.user32
        DESKTOP_SWITCHDESKTOP = 0x0100
        hdesk = user32.OpenInputDesktop(0, False, DESKTOP_SWITCHDESKTOP)
        if hdesk:
            user32.CloseDesktop(hdesk)
            return False
        return True
    except Exception:
        return False


def _window_minimized(hwnd: int) -> bool:
    if sys.platform != "win32" or not hwnd:
        return False
    try:
        import ctypes

        return bool(ctypes.windll.user32.IsIconic(int(hwnd)))
    except Exception:
        return False


def do_check_session_status(
    window_title: Optional[str] = None,
    app_id: str = "",
) -> dict[str, Any]:
    """Report target window, HWND liveness, lock/minimize state, and MCP readiness."""
    from tools.app_session import resolve_scope
    from tools.target_window import get_target
    from tools.windows import resolve_window_handle

    wt, hwnd_from_app, err = resolve_scope(app_id, window_title)
    if err:
        return err
    target = (wt or get_target() or "").strip()
    hwnd = int(hwnd_from_app or 0)
    if target and not hwnd:
        resolved = resolve_window_handle(target)
        if resolved:
            hwnd = int(resolved)
    alive = False
    minimized = False
    if hwnd:
        alive = True
        minimized = _window_minimized(hwnd)
    elif target:
        resolved = resolve_window_handle(target)
        if resolved:
            hwnd = int(resolved)
            alive = True
            minimized = _window_minimized(hwnd)

    locked = _workstation_locked() if sys.platform == "win32" else False
    spy_available = False
    if sys.platform == "win32":
        try:
            from tools.spy_bridge import spy_available as _spy_ok

            spy_available = bool(_spy_ok())
        except Exception:
            spy_available = False

    operations = {
        "uia_find": alive and not locked,
        "click": alive and not locked and not minimized,
        "type_text": alive and not locked and not minimized,
        "screenshot": not locked,
    }

    return {
        "success": True,
        "target_set": bool(target),
        "target_window": target,
        "target_hwnd": hwnd,
        "target_alive": alive,
        "target_minimized": minimized,
        "app_id": app_id or "",
        "session_locked": locked,
        "operations_available": operations,
        "platform": sys.platform,
        "spy_available": spy_available,
        "mcp_server": True,
    }


def do_attach_to_app(process_name: str) -> dict[str, Any]:
    from tools.windows import do_list_windows

    needle = (process_name or "").strip().lower()
    if not needle:
        return {"success": False, "error": "process_name is required"}

    windows = do_list_windows()
    matches = [
        w
        for w in windows
        if needle in str(w.get("process") or "").lower()
        or needle in str(w.get("title") or "").lower()
    ]
    if not matches:
        return {"success": False, "error": f"No running window for '{process_name}'"}
    from tools.app_session import register_window

    return register_window(matches[0])


def do_attach_to_pid(pid: int) -> dict[str, Any]:
    from tools.windows import do_list_windows

    if not pid:
        return {"success": False, "error": "pid is required"}
    windows = do_list_windows()
    matches = [w for w in windows if int(w.get("pid") or 0) == int(pid)]
    if not matches:
        return {"success": False, "error": f"No window for pid {pid}"}
    from tools.app_session import register_window

    return register_window(matches[0])


def do_list_apps() -> dict[str, Any]:
    from tools.app_session import list_registered_apps

    apps = []
    for app_id, meta in list_registered_apps().items():
        apps.append({"app_id": app_id, **meta})
    return {"success": True, "count": len(apps), "apps": apps}


def do_close_app(app_id: str) -> dict[str, Any]:
    from tools.app_session import get_app, unregister_app

    app = get_app(app_id)
    if not app:
        return {"success": False, "error": f"Unknown app_id: {app_id}"}
    pid = int(app.get("pid") or 0)
    if sys.platform == "win32" and pid:
        try:
            import ctypes

            PROCESS_TERMINATE = 0x0001
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
            if handle:
                ctypes.windll.kernel32.TerminateProcess(handle, 0)
                ctypes.windll.kernel32.CloseHandle(handle)
        except Exception as exc:
            return {"success": False, "error": str(exc)}
    unregister_app(app_id)
    return {"success": True, "closed": app_id, "pid": pid}


def do_release_keyboard() -> dict[str, Any]:
    try:
        import pyautogui

        for key in ("shift", "ctrl", "alt", "win"):
            try:
                pyautogui.keyUp(key)
            except Exception:
                pass
    except Exception:
        pass
    return {"success": True, "released": True}


def do_release_all() -> dict[str, Any]:
    """Clear target window, caches, highlight overlay, and event monitors."""
    from detection.orchestrator import clear_tree_cache
    from detection.uia_tree_cache import invalidate_all
    from tools.event_monitor import do_stop_event_monitor
    from tools.highlight import clear_highlight
    from tools.target_window import set_target
    from tools.window_classify import invalidate_cache as invalidate_classify_cache

    set_target("")
    invalidate_all()
    clear_tree_cache()
    invalidate_classify_cache()
    clear_highlight()
    do_stop_event_monitor()
    try:
        do_release_keyboard()
    except Exception:
        pass
    try:
        from tools.event_sidecar_bridge import shutdown_sidecar

        shutdown_sidecar()
    except Exception:
        pass
    return {"success": True, "released": True}


def register(server) -> int:
    """Register session tools on *server*."""
    from tools.params import resolve_scoped_window, resolve_window_title as _wt
    from tools.safety import ActionTimeoutError, with_timeout

    @server.tool()
    def check_session_status(
        window_title: str = "",
        title: str = "",
        app_id: str = "",
    ) -> str:
        """Report session health: target alive, locked desktop, minimized, operations."""
        import json

        wt, _hwnd, scope_err = resolve_scoped_window(app_id, window_title, title, 0)
        if scope_err:
            return f"ERROR: {scope_err}"
        try:
            result = with_timeout(
                lambda: do_check_session_status(window_title=wt, app_id=app_id),
                timeout=10.0,
            )
        except ActionTimeoutError as exc:
            return f"ERROR: {exc}"
        return json.dumps(result, ensure_ascii=False)

    @server.tool()
    def release_all() -> str:
        """Release target window, caches, highlights, and active event monitors."""
        result = do_release_all()
        if result.get("success"):
            return "OK released session resources"
        return "FAIL release_all"

    @server.tool()
    def attach_to_app(process_name: str) -> str:
        """Attach to a running process by name. Returns app_id for scoped tools."""
        import json

        try:
            result = with_timeout(lambda: do_attach_to_app(process_name), timeout=10.0)
        except ActionTimeoutError:
            return "Timed out attaching to app."
        return json.dumps(result, ensure_ascii=False)

    @server.tool()
    def attach_to_pid(pid: int) -> str:
        """Attach to a running process by PID. Returns app_id."""
        import json

        try:
            result = with_timeout(lambda: do_attach_to_pid(pid), timeout=10.0)
        except ActionTimeoutError:
            return "Timed out attaching to pid."
        return json.dumps(result, ensure_ascii=False)

    @server.tool()
    def list_apps() -> str:
        """List app_id sessions created by attach_to_app / attach_to_pid."""
        import json

        return json.dumps(do_list_apps(), ensure_ascii=False)

    @server.tool()
    def close_app(app_id: str) -> str:
        """Close application registered under app_id and remove session."""
        import json

        try:
            result = with_timeout(lambda: do_close_app(app_id), timeout=10.0)
        except ActionTimeoutError:
            return "Timed out closing app."
        return json.dumps(result, ensure_ascii=False)

    @server.tool()
    def release_keyboard() -> str:
        """Release stuck modifier keys (shift/ctrl/alt/win)."""
        import json

        return json.dumps(do_release_keyboard(), ensure_ascii=False)

    return 7

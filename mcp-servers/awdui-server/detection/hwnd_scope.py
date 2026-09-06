"""HWND-scoped window resolution for modals and MDI children."""
from __future__ import annotations

import sys
from typing import Any, Optional


def _window_from_hwnd(hwnd: int):
    if sys.platform != "win32" or not hwnd:
        return None
    try:
        from pywinauto import Desktop

        return Desktop(backend="uia").window(handle=int(hwnd))
    except Exception:
        return None


def validate_hwnd_in_target(hwnd: int, window_title: Optional[str] = None) -> tuple[bool, str]:
    """Best-effort check that *hwnd* belongs to the target app process."""
    if sys.platform != "win32" or not hwnd:
        return False, "invalid hwnd"
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        if not user32.IsWindow(int(hwnd)):
            return False, "hwnd is not a valid window"

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(int(hwnd), ctypes.byref(pid))
        if not pid.value:
            return False, "cannot resolve window process"

        title = (window_title or "").strip()
        if not title:
            return True, ""

        from tools.windows import resolve_window_handle

        parent_hwnd = resolve_window_handle(title)
        if not parent_hwnd:
            return True, ""

        parent_pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(int(parent_hwnd), ctypes.byref(parent_pid))
        if parent_pid.value and pid.value != parent_pid.value:
            return False, "hwnd process differs from target window"
        return True, ""
    except Exception as exc:
        return True, str(exc)


def resolve_window_from_hwnd(hwnd: int) -> dict[str, Any]:
    """Resolve HWND to title and liveness metadata."""
    if sys.platform != "win32":
        return {"success": False, "error": "HWND scope is Windows-only"}
    if not hwnd or int(hwnd) <= 0:
        return {"success": False, "error": "Invalid HWND"}

    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        handle = int(hwnd)
        if not user32.IsWindow(handle):
            return {"success": False, "error": "Invalid HWND"}

        length = user32.GetWindowTextLengthW(handle)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(handle, buf, length + 1)
        title = buf.value or ""

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))
        minimized = bool(user32.IsIconic(handle))
        visible = bool(user32.IsWindowVisible(handle))

        wrapper = _window_from_hwnd(handle)
        class_name = ""
        if wrapper is not None:
            try:
                class_name = wrapper.class_name() or ""
            except Exception:
                pass

        return {
            "success": True,
            "hwnd": handle,
            "title": title,
            "class_name": class_name,
            "process_id": int(pid.value or 0),
            "visible": visible,
            "minimized": minimized,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}

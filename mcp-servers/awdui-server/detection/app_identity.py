"""Resolve stable application identity for repository storage and framework detection."""
from __future__ import annotations

import sys
from typing import Optional

_SHELL_PROCESSES = frozenset({"applicationframehost.exe"})
_SHELL_CLASS_PREFIXES = (
    "applicationframewindow",
    "windows.ui.core.corewindow",
)


def _is_shell_process(process_name: str) -> bool:
    return (process_name or "").lower() in _SHELL_PROCESSES


def _is_shell_class(class_name: str) -> bool:
    cls = (class_name or "").lower()
    return any(cls.startswith(prefix) for prefix in _SHELL_CLASS_PREFIXES)


def title_app_name(window_title: Optional[str]) -> str:
    """Derive a human-readable app label from a window title."""
    raw = (window_title or "").strip()
    if not raw:
        return ""
    token = raw.split(" - ")[0].split("|")[0].strip()
    return token


def _full_exe_path_for_pid(pid: int) -> str:
    if pid <= 0 or sys.platform != "win32":
        return ""
    import ctypes
    import ctypes.wintypes

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = ctypes.wintypes.DWORD(1024)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return buf.value
        return ""
    finally:
        kernel32.CloseHandle(handle)


def _pid_for_hwnd(hwnd: int) -> int:
    if not hwnd or sys.platform != "win32":
        return 0
    import ctypes
    import ctypes.wintypes

    pid = ctypes.wintypes.DWORD()
    ctypes.windll.user32.GetWindowThreadProcessId(int(hwnd), ctypes.byref(pid))
    return int(pid.value)


def _child_hwnds(parent_hwnd: int) -> list[int]:
    if not parent_hwnd or sys.platform != "win32":
        return []
    import ctypes

    user32 = ctypes.windll.user32
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    children: list[int] = []

    def callback(hwnd, _lparam):
        children.append(int(hwnd))
        return True

    user32.EnumChildWindows(int(parent_hwnd), WNDENUMPROC(callback), 0)
    return children


def _window_title_for_hwnd(hwnd: int) -> str:
    if not hwnd or sys.platform != "win32":
        return ""
    import ctypes

    user32 = ctypes.windll.user32
    length = user32.GetWindowTextLengthW(int(hwnd))
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(int(hwnd), buf, length + 1)
    return buf.value


def _find_non_shell_window(window_title: str) -> Optional[dict]:
    """Prefer the real UWP process window over ApplicationFrameHost."""
    from tools.windows import do_list_windows

    title_lower = (window_title or "").lower()
    if not title_lower:
        return None

    best: Optional[dict] = None
    shell: Optional[dict] = None
    for win in do_list_windows():
        win_title = (win.get("title") or "").lower()
        if title_lower not in win_title and win_title not in title_lower:
            continue
        proc = (win.get("process_name") or "").lower()
        if _is_shell_process(proc):
            shell = shell or win
            continue
        if proc:
            return win
        best = best or win
    return best or shell


def _resolve_uwp_core_from_shell(shell_hwnd: int) -> tuple[str, str, int]:
    """Walk child CoreWindow HWNDs to find the packaged app process."""
    from tools.window_classify import _get_class_name, _get_process_name

    for child in _child_hwnds(shell_hwnd):
        cls = _get_class_name(child)
        if "corewindow" not in cls.lower():
            continue
        proc = _get_process_name(child)
        if proc and not _is_shell_process(proc):
            pid = _pid_for_hwnd(child)
            return proc, _full_exe_path_for_pid(pid), pid
    return "", "", 0


def resolve_app_identity(
    window_title: Optional[str] = None,
    hwnd: Optional[int] = None,
) -> dict:
    """Return stable app identity for repository storage.

    Keys: app_name, exe_name, process_name, exe_path, window_title, is_uwp_shell
    """
    empty = {
        "app_name": "",
        "exe_name": "",
        "process_name": "",
        "exe_path": "",
        "window_title": window_title or "",
        "is_uwp_shell": False,
    }
    if sys.platform != "win32":
        name = title_app_name(window_title)
        return {
            **empty,
            "app_name": name,
            "exe_name": name,
            "window_title": window_title or "",
        }

    from tools.window_classify import _get_class_name, _get_process_name
    from tools.framework_detect import _get_hwnd_for_window

    resolved_hwnd = int(hwnd or 0) or int(_get_hwnd_for_window(window_title) or 0)
    if not resolved_hwnd:
        name = title_app_name(window_title)
        return {
            **empty,
            "app_name": name,
            "exe_name": name,
            "window_title": window_title or "",
        }

    resolved_title = (window_title or _window_title_for_hwnd(resolved_hwnd)).strip()
    process_name = _get_process_name(resolved_hwnd)
    class_name = _get_class_name(resolved_hwnd)
    pid = _pid_for_hwnd(resolved_hwnd)
    exe_path = _full_exe_path_for_pid(pid)
    is_shell = _is_shell_process(process_name) or _is_shell_class(class_name)

    if is_shell:
        core_proc, core_path, core_pid = _resolve_uwp_core_from_shell(resolved_hwnd)
        if core_proc:
            process_name = core_proc
            exe_path = core_path
            pid = core_pid
            is_shell = False
        else:
            sibling = _find_non_shell_window(resolved_title)
            if sibling:
                sibling_proc = sibling.get("process_name") or ""
                if sibling_proc and not _is_shell_process(sibling_proc):
                    process_name = sibling_proc
                    sibling_pid = int(sibling.get("pid") or 0)
                    if sibling_pid:
                        pid = sibling_pid
                        exe_path = _full_exe_path_for_pid(pid)
                    is_shell = False

    title_name = title_app_name(resolved_title)
    if process_name and not _is_shell_process(process_name):
        app_name = process_name
    elif title_name:
        app_name = title_name
    elif process_name:
        app_name = process_name
    else:
        app_name = "unknown"

    exe_name = app_name.rsplit("\\", 1)[-1] if "\\" in app_name else app_name
    if exe_name.lower().endswith(".exe"):
        pass
    elif exe_path:
        exe_name = exe_path.rsplit("\\", 1)[-1]

    return {
        "app_name": app_name,
        "exe_name": exe_name,
        "process_name": process_name,
        "exe_path": exe_path,
        "window_title": resolved_title,
        "is_uwp_shell": is_shell,
    }


def repository_app_name(
    framework: dict,
    window_title: Optional[str] = None,
) -> tuple[str, str]:
    """Return (app_name, exe_path) for SQLite repository keys."""
    identity = framework
    if not identity.get("app_name"):
        identity = {
            **framework,
            **resolve_app_identity(window_title or framework.get("window_title")),
        }

    app_name = (
        identity.get("app_name")
        or identity.get("exe_name")
        or identity.get("process_name")
        or title_app_name(window_title or identity.get("window_title"))
        or "unknown"
    )
    proc = (identity.get("process_name") or app_name or "").lower()
    if _is_shell_process(proc):
        title_name = title_app_name(window_title or identity.get("window_title"))
        app_name = title_name or "unknown"

    exe_path = identity.get("exe_path") or ""
    if _is_shell_process((identity.get("process_name") or "").lower()) and title_app_name(
        window_title or identity.get("window_title")
    ):
        # UWP shell only: hash by title, not ApplicationFrameHost.exe
        exe_path = ""

    return app_name, exe_path

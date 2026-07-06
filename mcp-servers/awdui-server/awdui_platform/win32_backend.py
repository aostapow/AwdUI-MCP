"""Win32 platform backend for AwdUI.

Native Windows APIs via ctypes — window enumeration, focus, DPI, process info.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes
from typing import List, Optional

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
advapi32 = ctypes.windll.advapi32
shcore = ctypes.windll.shcore

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TOKEN_QUERY = 0x0008
TokenElevation = 20

EnumWindowsProc = ctypes.WINFUNCTYPE(
    ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
)

_dpi_aware_set = False
PW_RENDERFULLCONTENT = 2


def set_process_dpi_aware() -> None:
    """Enable per-monitor DPI awareness so window rects match screen pixels."""
    global _dpi_aware_set
    if _dpi_aware_set:
        return
    try:
        # PROCESS_PER_MONITOR_DPI_AWARE = 2
        shcore.SetProcessDpiAwareness(2)
        _dpi_aware_set = True
        return
    except Exception:
        pass
    try:
        user32.SetProcessDPIAware()
        _dpi_aware_set = True
    except Exception:
        pass


def get_dpi_for_hwnd(hwnd: int) -> float:
    """DPI scale for a specific window (1.0 = 96 DPI)."""
    if hwnd:
        try:
            dpi = user32.GetDpiForWindow(int(hwnd))
            if dpi > 0:
                return dpi / 96.0
        except Exception:
            pass
    return _monitor_dpi_scale(hwnd or get_foreground_hwnd())


def _monitor_dpi_scale(hwnd: int = 0) -> float:
    try:
        if hwnd:
            monitor = user32.MonitorFromWindow(int(hwnd), 2)
        else:
            monitor = user32.MonitorFromWindow(0, 2)
        dpi_x = ctypes.c_uint()
        dpi_y = ctypes.c_uint()
        if shcore.GetDpiForMonitor(monitor, 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y)) == 0:
            return dpi_x.value / 96.0
    except Exception:
        pass
    try:
        hdc = user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)
        user32.ReleaseDC(0, hdc)
        return dpi / 96.0
    except Exception:
        return 1.0


def get_dpi_scale() -> float:
    """Return DPI scale for the monitor containing the foreground window."""
    return get_dpi_for_hwnd(get_foreground_hwnd())


def get_window_rect(hwnd: int) -> Optional[dict]:
    """Return physical screen rect {x, y, w, h} for a window."""
    if not hwnd:
        return None
    rect = ctypes.wintypes.RECT()
    if not user32.GetWindowRect(int(hwnd), ctypes.byref(rect)):
        return None
    w = rect.right - rect.left
    h = rect.bottom - rect.top
    if w <= 0 or h <= 0:
        return None
    return {"x": rect.left, "y": rect.top, "w": w, "h": h}


def force_window_foreground(hwnd: int) -> bool:
    """Bring *hwnd* to the foreground (works from background automation processes)."""
    if not hwnd:
        return False
    import time

    set_process_dpi_aware()
    ASFW_ANY = -1
    try:
        user32.AllowSetForegroundWindow(ASFW_ANY)
    except Exception:
        pass

    fg_hwnd = user32.GetForegroundWindow()
    fg_tid = user32.GetWindowThreadProcessId(fg_hwnd, None)
    our_tid = kernel32.GetCurrentThreadId()
    attached = False
    if fg_tid and fg_tid != our_tid:
        attached = bool(user32.AttachThreadInput(our_tid, fg_tid, True))

    user32.ShowWindow(int(hwnd), 9)  # SW_RESTORE
    user32.BringWindowToTop(int(hwnd))
    user32.SetForegroundWindow(int(hwnd))
    try:
        user32.SwitchToThisWindow(int(hwnd), True)
    except Exception:
        pass

    if attached:
        user32.AttachThreadInput(our_tid, fg_tid, False)

    for _ in range(50):
        time.sleep(0.01)
        if user32.GetForegroundWindow() == int(hwnd):
            return True
    return is_window_in_foreground(int(hwnd))


def is_window_in_foreground(hwnd: int, title_hint: str = "") -> bool:
    """True if *hwnd* (or its UWP root/child) is the active window."""
    if not hwnd:
        return False
    fg = get_foreground_hwnd()
    if not fg:
        return False
    if int(hwnd) == int(fg):
        return True
    GA_ROOT = 2
    try:
        if user32.GetAncestor(fg, GA_ROOT) == int(hwnd):
            return True
        if user32.GetAncestor(int(hwnd), GA_ROOT) == fg:
            return True
    except Exception:
        pass
    if title_hint:
        fg_title = get_foreground_title().lower()
        hint = title_hint.lower()
        if hint in fg_title or fg_title in hint:
            return True
    return False


def capture_window_image(hwnd: int):
    """Capture the full window via PrintWindow. Returns PIL.Image or None."""
    from PIL import Image

    rect = get_window_rect(hwnd)
    if not rect:
        return None
    w, h = rect["w"], rect["h"]

    hwnd_dc = user32.GetWindowDC(int(hwnd))
    if not hwnd_dc:
        return None
    gdi32 = ctypes.windll.gdi32
    mem_dc_handle = gdi32.CreateCompatibleDC(hwnd_dc)
    if not mem_dc_handle:
        user32.ReleaseDC(int(hwnd), hwnd_dc)
        return None
    bmp = None
    old_obj = None
    try:
        bmp = gdi32.CreateCompatibleBitmap(hwnd_dc, w, h)
        if not bmp:
            return None
        old_obj = gdi32.SelectObject(mem_dc_handle, bmp)
        if not user32.PrintWindow(int(hwnd), mem_dc_handle, PW_RENDERFULLCONTENT):
            user32.PrintWindow(int(hwnd), mem_dc_handle, 0)

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ("biSize", ctypes.c_uint32),
                ("biWidth", ctypes.c_int32),
                ("biHeight", ctypes.c_int32),
                ("biPlanes", ctypes.c_uint16),
                ("biBitCount", ctypes.c_uint16),
                ("biCompression", ctypes.c_uint32),
                ("biSizeImage", ctypes.c_uint32),
                ("biXPelsPerMeter", ctypes.c_int32),
                ("biYPelsPerMeter", ctypes.c_int32),
                ("biClrUsed", ctypes.c_uint32),
                ("biClrImportant", ctypes.c_uint32),
            ]

        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = w
        bmi.biHeight = -h  # top-down bitmap
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0  # BI_RGB

        buf = ctypes.create_string_buffer(w * h * 4)
        lines = gdi32.GetDIBits(
            mem_dc_handle, bmp, 0, h, buf, ctypes.byref(bmi), 0
        )
        if not lines:
            return None
        return Image.frombuffer("RGB", (w, h), buf, "raw", "BGRX", 0, 1)
    finally:
        if old_obj is not None:
            gdi32.SelectObject(mem_dc_handle, old_obj)
        if bmp:
            gdi32.DeleteObject(bmp)
        gdi32.DeleteDC(mem_dc_handle)
        user32.ReleaseDC(int(hwnd), hwnd_dc)


def get_foreground_hwnd() -> int:
    return user32.GetForegroundWindow()


def get_foreground_title() -> str:
    hwnd = get_foreground_hwnd()
    length = user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def get_process_name_for_pid(pid: int) -> str:
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(260)
        size = ctypes.wintypes.DWORD(260)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            path = buf.value
            return path.rsplit("\\", 1)[-1] if "\\" in path else path
        return ""
    finally:
        kernel32.CloseHandle(handle)


def get_class_name(hwnd) -> str:
    if not hwnd:
        return ""
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(int(hwnd), buf, 256)
    return buf.value


def is_elevated(pid: int = None) -> bool:
    if pid is None:
        pid = kernel32.GetCurrentProcessId()
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return True
    try:
        token = ctypes.wintypes.HANDLE()
        if not advapi32.OpenProcessToken(handle, TOKEN_QUERY, ctypes.byref(token)):
            return False
        try:
            elevation = ctypes.wintypes.DWORD()
            size = ctypes.wintypes.DWORD()
            advapi32.GetTokenInformation(
                token, TokenElevation, ctypes.byref(elevation),
                ctypes.sizeof(elevation), ctypes.byref(size),
            )
            return elevation.value != 0
        finally:
            kernel32.CloseHandle(token)
    finally:
        kernel32.CloseHandle(handle)


def _enum_visible_windows() -> list[tuple[int, dict]]:
    """Return (hwnd, info_dict) for visible titled windows."""
    set_process_dpi_aware()
    results: list[tuple[int, dict]] = []

    def callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        if not title:
            return True
        rect = ctypes.wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        pid = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        proc_name = get_process_name_for_pid(pid.value)
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        info = {
            "title": title,
            "process_name": proc_name,
            "class_name": get_class_name(hwnd),
            "x": rect.left,
            "y": rect.top,
            "width": w,
            "height": h,
            "hwnd": int(hwnd),
            "pid": pid.value,
        }
        client = ctypes.wintypes.RECT()
        user32.GetClientRect(hwnd, ctypes.byref(client))
        pt = ctypes.wintypes.POINT(0, 0)
        user32.ClientToScreen(hwnd, ctypes.byref(pt))
        info["client_x"] = pt.x
        info["client_y"] = pt.y
        info["client_width"] = client.right - client.left
        info["client_height"] = client.bottom - client.top
        info["dpi_scale"] = round(get_dpi_for_hwnd(int(hwnd)), 2)
        results.append((hwnd, info))
        return True

    user32.EnumWindows(EnumWindowsProc(callback), 0)
    return results


def list_windows_native() -> List[dict]:
    return [info for _, info in _enum_visible_windows()]


def focus_window_native(title: str, action: str) -> dict:
    from tools.windows import find_matching_window

    all_hwnds = _enum_visible_windows()
    match = find_matching_window(title, [info for _, info in all_hwnds])
    if match["window"] is None:
        return {"success": False, "error": f"No window matching '{title}' found"}

    matched_title = match["window"]["title"]
    target_hwnd = None
    for hwnd, info in all_hwnds:
        if info["title"] == matched_title:
            target_hwnd = hwnd
            break
    if target_hwnd is None:
        return {"success": False, "error": f"No window matching '{title}' found"}

    SW_MINIMIZE, SW_MAXIMIZE, SW_RESTORE, SW_SHOW = 6, 3, 9, 5

    if action == "focus":
        force_window_foreground(int(target_hwnd))
    elif action == "minimize":
        user32.ShowWindow(target_hwnd, SW_MINIMIZE)
    elif action == "maximize":
        user32.ShowWindow(target_hwnd, SW_MAXIMIZE)
    elif action == "restore":
        user32.ShowWindow(target_hwnd, SW_RESTORE)
    else:
        return {"success": False, "error": f"Unknown action: {action}"}

    return {"success": True, "window": matched_title, "action": action}


def classify_window_native(handle=None) -> dict:
    from tools.window_classify import classify_window
    hwnd = int(handle) if handle else get_foreground_hwnd()
    return classify_window(hwnd)


def get_loaded_modules(pid) -> list[str]:
    """Return basenames of DLLs loaded in a process."""
    import sys
    if sys.maxsize <= 2**32:
        LIST_MODULES_ALL = 0x03
    else:
        LIST_MODULES_ALL = 0x03

    psapi = ctypes.windll.psapi
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | 0x0400, False, pid)
    if not handle:
        return []
    try:
        needed = ctypes.wintypes.DWORD()
        psapi.EnumProcessModulesEx(handle, None, 0, ctypes.byref(needed), LIST_MODULES_ALL)
        count = needed.value // ctypes.sizeof(ctypes.c_void_p)
        if count == 0:
            return []
        arr = (ctypes.c_void_p * count)()
        psapi.EnumProcessModulesEx(
            handle, ctypes.byref(arr), ctypes.sizeof(arr),
            ctypes.byref(needed), LIST_MODULES_ALL,
        )
        modules = []
        buf = ctypes.create_unicode_buffer(260)
        for i in range(count):
            if psapi.GetModuleBaseNameW(handle, arr[i], buf, 260):
                modules.append(buf.value)
        return modules
    except Exception:
        return []
    finally:
        kernel32.CloseHandle(handle)


def run_ocr_native(image_path: str) -> list[dict]:
    raise NotImplementedError("win32_backend: use tools.ocr RapidOCR/Windows OCR")


def send_text_to_console(pid, text, hwnd=0) -> dict:
    raise NotImplementedError("win32_backend: use tools.input_tools console routing")


def send_keys_to_console(pid, keys, hwnd=0) -> dict:
    raise NotImplementedError("win32_backend: use tools.input_tools console routing")


def find_host_terminal_hwnd() -> int | None:
    for hwnd, info in _enum_visible_windows():
        proc = (info.get("process_name") or "").lower()
        if proc in ("windowsterminal.exe", "wt.exe", "powershell.exe", "cmd.exe"):
            return hwnd
    return None

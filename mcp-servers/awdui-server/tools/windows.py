"""Window tools -- list, focus, and launch application windows.

Provides cross-platform window management using native APIs per platform:
    - Windows: Win32 via ctypes (EnumWindows, SetForegroundWindow, etc.)
    - macOS:   AppleScript via subprocess
    - Linux:   wmctrl via subprocess

Core functions:
    do_list_windows   - enumerate visible windows with geometry
    do_focus_window   - find window by partial title, perform action
    do_launch_app     - launch an application via subprocess.Popen

MCP registration:
    register          - wire list_windows, focus_window, launch_app on a Server
"""

import platform
import subprocess
import shlex
from typing import Any, List, Optional


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def get_platform() -> str:
    """Return 'windows', 'darwin', or 'linux'."""
    p = platform.system().lower()
    if p == "windows":
        return "windows"
    elif p == "darwin":
        return "darwin"
    else:
        return "linux"


def validate_window_action(action: str) -> str:
    """Validate and normalise a window action string.

    Raises :class:`ValueError` if *action* is not one of
    ``focus``, ``minimize``, ``maximize``, ``restore``.
    """
    valid = ("focus", "minimize", "maximize", "restore")
    if action.lower() not in valid:
        raise ValueError(
            f"Invalid action '{action}'. Must be one of: {valid}"
        )
    return action.lower()


def get_foreground_title() -> str:
    """Return the title of the current foreground window.

    Returns an empty string on non-Windows platforms or on failure.
    """
    if get_platform() == "darwin":
        from awdui_platform import get_foreground_title as _darwin_title
        return _darwin_title()
    if get_platform() == "windows":
        from awdui_platform import get_foreground_title as _win_title
        return _win_title()
    return ""


def find_matching_window(title: str, windows: list[dict]) -> dict:
    """Find a window by title using case-insensitive substring matching.

    Falls back to matching against the process executable name when no
    title match is found (e.g. query "steam" matches process "steam.exe").

    Returns:
        {"window": dict, "match_quality": "exact"|"process_name"} on match, or
        {"window": None, "available": [str, ...]} listing all window titles.
    """
    if not windows:
        return {"window": None, "available": []}

    title_lower = title.lower()
    available = [w["title"] for w in windows]

    candidates = [w for w in windows if title_lower in w["title"].lower()]
    if not candidates:
        candidates = []
        for win in windows:
            proc = win.get("process_name", "")
            if proc:
                stem = proc.rsplit(".", 1)[0].lower()
                if title_lower == stem or title_lower in stem:
                    candidates.append(win)
        if candidates:
            best = _best_window_candidate(candidates, title_lower)
            return {"window": best, "match_quality": "process_name"}

        return {"window": None, "available": available}

    best = _best_window_candidate(candidates, title_lower)
    return {"window": best, "match_quality": "exact"}


def resolve_window_handle(window_title: Optional[str] = None) -> Optional[int]:
    """Resolve a visible top-level HWND for *window_title* (UWP-aware).

    Uses ``set_target_window`` when *window_title* is empty.
    """
    from tools.target_window import get_target

    title = (window_title or get_target() or "").strip()
    if not title:
        return None
    match = find_matching_window(title, do_list_windows())
    win = match.get("window")
    if not win:
        return None
    hwnd = win.get("hwnd")
    return int(hwnd) if hwnd else None


def resolve_window_visual_rect(window_title: Optional[str] = None) -> Optional[dict]:
    """Screen bounding box for UIA enumeration (UWP: prefer ApplicationFrameHost).

    CoreWindow UIA bounds are often smaller than the visible host frame; controls
    like Calculator numpad buttons can sit outside CoreWindow but inside the frame.
    """
    from tools.target_window import get_target

    title = (window_title or get_target() or "").strip()
    if not title:
        return None
    title_lower = title.lower()
    candidates = [
        w for w in do_list_windows()
        if title_lower in (w.get("title") or "").lower()
    ]
    if not candidates:
        match = find_matching_window(title, do_list_windows())
        win = match.get("window")
        if not win:
            return None
        candidates = [win]

    def score(win: dict) -> int:
        s = 0
        proc = (win.get("process_name") or "").lower()
        if title_lower in ("calculadora", "calculator"):
            if "applicationframehost" in proc:
                s += 20000
            elif "calculatorapp" in proc:
                s += 5000
        x, y = win.get("x", 0), win.get("y", 0)
        if x > 0 and y > 0:
            s += 1000
        area = max(0, win.get("width", 0)) * max(0, win.get("height", 0))
        s += area // 500
        return s

    best = max(candidates, key=score)
    return {
        "x": int(best.get("x", 0)),
        "y": int(best.get("y", 0)),
        "w": int(best.get("width", 0)),
        "h": int(best.get("height", 0)),
    }


def _best_window_candidate(
    windows: list[dict],
    title_hint: str = "",
    *,
    purpose: str = "handle",
) -> dict:
    """Pick the best window when several share the same title (common for UWP).

    purpose:
        handle — HWND/UIA attach (prefer CoreWindow / CalculatorApp.exe)
        visual — screenshot bounds (prefer ApplicationFrameHost frame)
    """
    hint = title_hint.lower()
    prefer_visual = purpose == "visual"

    def score(win: dict) -> int:
        s = 0
        win_title = (win.get("title") or "").lower()
        if hint and win_title == hint:
            s += 10000
        elif hint and (win_title.startswith(hint) or win_title.endswith(hint)):
            s += 2000
        proc = (win.get("process_name") or "").lower()
        if hint in ("calculadora", "calculator"):
            if prefer_visual:
                if "applicationframehost" in proc:
                    s += 12000
                elif "calculatorapp" in proc:
                    s += 8000
            else:
                if "calculatorapp" in proc:
                    s += 12000
                elif "applicationframehost" in proc:
                    s += 8000
        elif "applicationframehost" in proc:
            s += 1000
        x, y = win.get("x", 0), win.get("y", 0)
        if x > -1000 and y > -1000:
            s += 500
        area = max(0, win.get("width", 0)) * max(0, win.get("height", 0))
        s += area // 1000
        return s

    return max(windows, key=score)


# ------------------------------------------------------------------
# Platform-specific: list windows
# ------------------------------------------------------------------

def _get_process_name_win32(pid: int) -> str:
    """Get the executable name for a process ID. Returns '' on failure."""
    import ctypes
    import ctypes.wintypes

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    kernel32 = ctypes.windll.kernel32

    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(260)
        size = ctypes.wintypes.DWORD(260)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            # Extract just the filename from the full path
            path = buf.value
            return path.rsplit("\\", 1)[-1] if "\\" in path else path
        return ""
    finally:
        kernel32.CloseHandle(handle)


def _list_windows_win32() -> List[dict]:
    """List visible windows on Windows using Win32 EnumWindows via ctypes."""
    import ctypes
    import ctypes.wintypes

    user32 = ctypes.windll.user32

    EnumWindows = user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(
        ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
    )
    GetWindowTextW = user32.GetWindowTextW
    GetWindowTextLengthW = user32.GetWindowTextLengthW
    IsWindowVisible = user32.IsWindowVisible
    GetWindowRect = user32.GetWindowRect
    GetWindowThreadProcessId = user32.GetWindowThreadProcessId

    windows = []

    def enum_callback(hwnd, _lparam):
        if not IsWindowVisible(hwnd):
            return True
        length = GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        if not title:
            return True

        rect = ctypes.wintypes.RECT()
        GetWindowRect(hwnd, ctypes.byref(rect))

        # Get process name
        pid = ctypes.wintypes.DWORD()
        GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        proc_name = _get_process_name_win32(pid.value)

        windows.append({
            "title": title,
            "process_name": proc_name,
            "hwnd": int(hwnd),
            "x": rect.left,
            "y": rect.top,
            "width": rect.right - rect.left,
            "height": rect.bottom - rect.top,
        })
        return True

    EnumWindows(EnumWindowsProc(enum_callback), 0)
    return windows


def _list_windows_darwin() -> List[dict]:
    """List visible windows on macOS using AppleScript."""
    script = '''
    tell application "System Events"
        set windowList to ""
        repeat with proc in (every process whose visible is true)
            repeat with w in (every window of proc)
                set windowList to windowList & name of w & "||" & ¬
                    position of w & "||" & size of w & linefeed
            end repeat
        end repeat
        return windowList
    end tell
    '''
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=10
        )
        windows = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("||")
            if len(parts) >= 3:
                title = parts[0].strip()
                # Position comes as "x, y"
                pos_parts = parts[1].strip().split(", ")
                size_parts = parts[2].strip().split(", ")
                try:
                    windows.append({
                        "title": title,
                        "x": int(pos_parts[0]),
                        "y": int(pos_parts[1]),
                        "width": int(size_parts[0]),
                        "height": int(size_parts[1]),
                    })
                except (ValueError, IndexError):
                    continue
        return windows
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def _list_windows_linux() -> List[dict]:
    """List visible windows on Linux using wmctrl -lG."""
    try:
        result = subprocess.run(
            ["wmctrl", "-lG"],
            capture_output=True, text=True, timeout=10
        )
        windows = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            # wmctrl -lG format:
            # 0x04000007  0 100  200  800  600  hostname Title goes here
            parts = line.split(None, 7)
            if len(parts) >= 8:
                try:
                    windows.append({
                        "title": parts[7],
                        "x": int(parts[2]),
                        "y": int(parts[3]),
                        "width": int(parts[4]),
                        "height": int(parts[5]),
                    })
                except (ValueError, IndexError):
                    continue
        return windows
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


# ------------------------------------------------------------------
# Platform-specific: focus window
# ------------------------------------------------------------------

def _focus_window_win32(title: str, action: str) -> dict:
    """Focus/minimize/maximize/restore a window on Windows via Win32."""
    import ctypes
    import ctypes.wintypes

    user32 = ctypes.windll.user32

    EnumWindows = user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(
        ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
    )
    GetWindowTextW = user32.GetWindowTextW
    GetWindowTextLengthW = user32.GetWindowTextLengthW
    IsWindowVisible = user32.IsWindowVisible
    SetForegroundWindow = user32.SetForegroundWindow
    ShowWindow = user32.ShowWindow

    SW_MINIMIZE = 6
    SW_MAXIMIZE = 3
    SW_RESTORE = 9

    target_hwnd = None
    target_title = None
    title_lower = title.lower()

    # Collect all visible windows so we can use find_matching_window()
    # which supports both title substring and process-name fallback.
    all_hwnds = []  # parallel list of hwnds for each window dict

    def enum_callback(hwnd, _lparam):
        if not IsWindowVisible(hwnd):
            return True
        length = GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        GetWindowTextW(hwnd, buf, length + 1)
        win_title = buf.value
        if not win_title:
            return True

        # Get process name for fallback matching
        GetWindowThreadProcessId = user32.GetWindowThreadProcessId
        pid = ctypes.wintypes.DWORD()
        GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        proc_name = _get_process_name_win32(pid.value)

        all_hwnds.append((hwnd, {
            "title": win_title,
            "process_name": proc_name,
        }))
        return True

    EnumWindows(EnumWindowsProc(enum_callback), 0)

    # Use shared matching logic (title substring + process-name fallback)
    window_dicts = [info for _, info in all_hwnds]
    match = find_matching_window(title, window_dicts)

    if match["window"] is not None:
        matched_title = match["window"]["title"]
        # Find the hwnd for the matched window
        for hwnd, info in all_hwnds:
            if info["title"] == matched_title:
                target_hwnd = hwnd
                target_title = matched_title
                break

    if target_hwnd is None:
        available = match.get("available", [])
        return {"success": False, "error": f"No window matching '{title}' found"}

    if action == "focus":
        from awdui_platform.win32_backend import force_window_foreground

        force_window_foreground(int(target_hwnd))
    elif action == "minimize":
        ShowWindow(target_hwnd, SW_MINIMIZE)
    elif action == "maximize":
        ShowWindow(target_hwnd, SW_MAXIMIZE)
    elif action == "restore":
        ShowWindow(target_hwnd, SW_RESTORE)

    return {"success": True, "window": target_title, "action": action}


def _focus_window_darwin(title: str, action: str) -> dict:
    """Focus/minimize/maximize/restore a window on macOS via AppleScript."""
    title_escaped = title.replace('"', '\\"')

    if action == "focus":
        script = f'''
        tell application "System Events"
            set targetProc to first process whose visible is true and ¬
                (name of every window contains "{title_escaped}")
            set frontmost of targetProc to true
        end tell
        '''
    elif action == "minimize":
        script = f'''
        tell application "System Events"
            repeat with proc in (every process whose visible is true)
                repeat with w in (every window of proc)
                    if name of w contains "{title_escaped}" then
                        click (first button of w whose subrole is "AXMinimizeButton")
                        return "done"
                    end if
                end repeat
            end repeat
        end tell
        '''
    elif action == "maximize":
        script = f'''
        tell application "System Events"
            repeat with proc in (every process whose visible is true)
                repeat with w in (every window of proc)
                    if name of w contains "{title_escaped}" then
                        click (first button of w whose subrole is "AXZoomButton")
                        return "done"
                    end if
                end repeat
            end repeat
        end tell
        '''
    elif action == "restore":
        # On macOS, "restore" is essentially un-minimize
        script = f'''
        tell application "System Events"
            repeat with proc in (every process whose visible is true)
                repeat with w in (every window of proc)
                    if name of w contains "{title_escaped}" then
                        set frontmost of proc to true
                        return "done"
                    end if
                end repeat
            end repeat
        end tell
        '''
    else:
        return {"success": False, "error": f"Unknown action: {action}"}

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return {"success": True, "window": title, "action": action}
        else:
            return {
                "success": False,
                "error": result.stderr.strip() or f"No window matching '{title}' found",
            }
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return {"success": False, "error": str(exc)}


def _focus_window_linux(title: str, action: str) -> dict:
    """Focus/minimize/maximize/restore a window on Linux via wmctrl."""
    try:
        if action == "focus":
            result = subprocess.run(
                ["wmctrl", "-a", title],
                capture_output=True, text=True, timeout=10
            )
        elif action == "minimize":
            # wmctrl doesn't have a direct minimize; use xdotool fallback
            result = subprocess.run(
                ["xdotool", "search", "--name", title, "windowminimize"],
                capture_output=True, text=True, timeout=10
            )
        elif action == "maximize":
            result = subprocess.run(
                ["wmctrl", "-r", title, "-b", "add,maximized_vert,maximized_horz"],
                capture_output=True, text=True, timeout=10
            )
        elif action == "restore":
            result = subprocess.run(
                ["wmctrl", "-r", title, "-b", "remove,maximized_vert,maximized_horz"],
                capture_output=True, text=True, timeout=10
            )
        else:
            return {"success": False, "error": f"Unknown action: {action}"}

        if result.returncode == 0:
            return {"success": True, "window": title, "action": action}
        else:
            return {
                "success": False,
                "error": result.stderr.strip() or f"No window matching '{title}' found",
            }
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return {"success": False, "error": str(exc)}


# ------------------------------------------------------------------
# Core functions
# ------------------------------------------------------------------

def do_list_windows() -> List[dict]:
    """Enumerate visible windows with geometry.

    Returns a list of dicts, each with keys:
    ``title``, ``x``, ``y``, ``width``, ``height``, ``hwnd``, ``pid``,
    ``process_name``, ``class_name``, ``client_x``, ``client_y``,
    ``client_width``, ``client_height``, ``dpi_scale`` (Windows).
    """
    plat = get_platform()
    if plat == "windows":
        from awdui_platform import list_windows_native
        return list_windows_native()
    elif plat == "darwin":
        from awdui_platform import list_windows_native
        return list_windows_native()
    else:
        return _list_windows_linux()


def do_focus_window(title: str, action: str = "focus") -> dict:
    """Find a window by partial *title* match and perform *action*.

    Parameters
    ----------
    title : str
        Partial window title to search for (case-insensitive match).
    action : str
        One of ``focus``, ``minimize``, ``maximize``, ``restore``.

    Returns
    -------
    dict
        ``{"success": True, "window": str, "action": str}`` on success,
        ``{"success": False, "error": str}`` on failure.
    """
    action = validate_window_action(action)
    plat = get_platform()
    if plat == "windows":
        from awdui_platform import focus_window_native
        return focus_window_native(title, action)
    elif plat == "darwin":
        from awdui_platform import focus_window_native
        return focus_window_native(title, action)
    else:
        return _focus_window_linux(title, action)


def do_restore_window(
    window_title: Optional[str] = None,
    window_handle: Optional[int] = None,
) -> dict:
    """Restore (un-minimize) a window by title or HWND."""
    if get_platform() != "windows":
        return {"success": False, "error": "restore_window is Windows-only"}
    import ctypes

    hwnd = int(window_handle or 0) or resolve_window_handle(window_title)
    if not hwnd:
        return {"success": False, "error": "window not found"}
    user32 = ctypes.windll.user32
    user32.ShowWindow(int(hwnd), 9)
    user32.SetForegroundWindow(int(hwnd))
    return {"success": True, "hwnd": int(hwnd), "action": "restore"}


def do_list_app_windows(window_title: Optional[str] = None) -> list[dict]:
    """List visible windows that belong to the same process as the target app."""
    from tools.target_window import get_target
    from tools.window_scope import resolve_window_scope

    scope = resolve_window_scope(window_title or get_target())
    pid = (scope.get("window") or {}).get("process_id")
    if not pid:
        title = (window_title or get_target() or "").strip()
        if not title:
            return []
        match = find_matching_window(title, do_list_windows())
        target = match.get("window") or {}
        pid = target.get("pid") or target.get("process_id")
    if not pid:
        return []
    return [
        w
        for w in do_list_windows()
        if (w.get("pid") or w.get("process_id")) == pid
    ]


def do_launch_app(
    path: str,
    args: Optional[str] = None,
    *,
    reuse: bool = True,
    replace: bool = False,
) -> dict:
    """Launch an application at *path* with optional *args*.

    When *reuse* is True (default), an already-running instance is focused
    instead of spawning a duplicate. Extra duplicate windows/processes are
    closed automatically (e.g. multiple Calculator instances).

    When *replace* is True, existing instances are closed first, then a
    fresh process is started. Use for stale UIA recovery — never stack
    ``launch_app`` without ``replace`` on apps already open.

    Parameters
    ----------
    path : str
        Path or name of the executable to launch.
    args : str | None
        Space-separated arguments to pass to the executable.
    reuse : bool
        Focus existing instance when found (default True).
    replace : bool
        Close all existing instances before launching (default False).

    Returns
    -------
    dict
        ``{"success": True, "pid": int, "reused": bool?, ...}`` on success,
        ``{"success": False, "error": str}`` on failure.
    """
    if reuse or replace:
        try:
            from tools.app_launch import try_reuse_existing

            if reuse and not replace:
                reused = try_reuse_existing(path, replace=False)
                if reused:
                    try:
                        from tools.app_session import apply_scope_to_launch_result
                        return apply_scope_to_launch_result(reused, path)
                    except Exception:
                        return reused
            elif replace:
                try_reuse_existing(path, replace=True)
        except Exception:
            pass

    try:
        cmd = [path]
        if args:
            cmd.extend(shlex.split(args))
        proc = subprocess.Popen(cmd)
        try:
            from detection.orchestrator import invalidate_tree_cache
            invalidate_tree_cache()
        except Exception:
            pass
        result = {"success": True, "pid": proc.pid, "reused": False, "action": "launched"}
        try:
            from tools.app_session import apply_scope_to_launch_result
            result = apply_scope_to_launch_result(result, path)
        except Exception:
            pass
        return result
    except (FileNotFoundError, OSError) as exc:
        return {"success": False, "error": str(exc)}


def do_list_desktop_windows() -> dict[str, Any]:
    windows = do_list_windows()
    rows = []
    for w in windows:
        rows.append(
            {
                "hwnd": int(w.get("hwnd") or 0),
                "title": w.get("title", ""),
                "pid": int(w.get("pid") or 0),
                "process": w.get("process", ""),
                "x": w.get("x", 0),
                "y": w.get("y", 0),
                "width": w.get("width", 0),
                "height": w.get("height", 0),
            }
        )
    return {"success": True, "count": len(rows), "windows": rows}


# ------------------------------------------------------------------
# MCP tool registration
# ------------------------------------------------------------------

def register(server) -> int:
    """Register *list_windows*, *focus_window*, and *launch_app* tools.

    Returns the number of tools registered (3).
    """

    from tools.safety import with_timeout, ActionTimeoutError

    @server.tool()
    def list_windows(app_id: str = "") -> str:
        """List visible windows; optional app_id filters to that session's process."""
        try:
            windows = with_timeout(do_list_windows, timeout=5.0)
        except ActionTimeoutError:
            return "Timed out after 5s listing windows. The system may be unresponsive."
        if app_id:
            from tools.app_session import filter_windows_for_app, get_app

            if not get_app(app_id):
                return f"Unknown app_id: {app_id}"
            windows = filter_windows_for_app(windows, app_id)
        if not windows:
            return "No visible windows found."
        lines = []
        for w in windows:
            proc = w.get("process_name", "")
            cls = w.get("class_name", "")
            tag = f" [{cls}/{proc}]" if cls or proc else ""
            outer = f"outer:{w['x']},{w['y']} {w['width']}x{w['height']}"
            if w.get("client_width") is not None:
                outer += (
                    f" client:{w.get('client_x', w['x'])},{w.get('client_y', w['y'])}"
                    f" {w['client_width']}x{w['client_height']}"
                )
            if w.get("dpi_scale"):
                outer += f" dpi:{w['dpi_scale']}"
            lines.append(f"  {w['title']}{tag} {outer}")
        return f"Found {len(windows)} windows:\n" + "\n".join(lines)

    @server.tool()
    def focus_window(
        title: str = "",
        window_title: str = "",
        action: str = "focus",
    ) -> str:
        """Find a window by partial title and focus, minimize, maximize, or restore it.

        Parameters:
            title: Partial window title to search for (alias: window_title).
            window_title: Same as title — either parameter is accepted.
            action: One of "focus", "minimize", "maximize", "restore" (default "focus").
        """
        from tools.params import resolve_window_title
        resolved = resolve_window_title(window_title, title) or ""
        if not resolved:
            return "Failed: window title is required (use title or window_title)."
        try:
            result = with_timeout(
                lambda: do_focus_window(resolved, action=action),
                timeout=5.0,
            )
        except ActionTimeoutError:
            return f"Timed out after 5s trying to {action} window '{resolved}'. The window may be frozen."
        if result["success"]:
            return f"{result['action'].capitalize()}ed window: {result['window']}"
        return f"Failed: {result['error']}"

    @server.tool()
    def restore_window(
        window_title: str = "",
        title: str = "",
        window_handle: int = 0,
    ) -> str:
        """Restore (un-minimize) the target window before UIA interaction."""
        from tools.params import resolve_window_title as _wt

        result = do_restore_window(
            window_title=_wt(window_title, title),
            window_handle=window_handle or None,
        )
        if result.get("success"):
            return f"OK restored hwnd={result.get('hwnd')}"
        return f"Failed: {result.get('error', 'unknown')}"

    @server.tool()
    def launch_app(
        path: str,
        args: str = "",
        reuse: bool = True,
        replace: bool = False,
    ) -> str:
        """Launch an application (reuses existing instance by default).

        Parameters:
            path: Path or name of the executable to launch.
            args: Space-separated arguments (default "").
            reuse: If True (default), focus an already-running instance instead
                of opening a duplicate. Closes extra duplicate windows when found.
            replace: If True, close all existing instances first, then launch
                fresh. Use for stale UIA recovery — do not call launch_app
                repeatedly without replace on an app that is already open.
        """
        result = do_launch_app(
            path,
            args=args if args else None,
            reuse=reuse,
            replace=replace,
        )
        if not result["success"]:
            return f"Failed to launch {path}: {result['error']}"
        if result.get("reused"):
            extra = int(result.get("closed_extra") or 0)
            title = result.get("window_title") or path
            msg = f"Reused {title} (PID {result['pid']})"
            if extra:
                msg += f"; closed {extra} duplicate instance(s)"
        else:
            msg = f"Launched {path} (PID {result['pid']})"
        if result.get("app_id"):
            msg += f" app_id={result['app_id']}"
        return msg

    @server.tool()
    def list_desktop_windows() -> str:
        """List top-level windows with HWND, title, PID, and geometry."""
        try:
            result = with_timeout(do_list_desktop_windows, timeout=15.0)
        except ActionTimeoutError:
            return "Timed out listing desktop windows."
        lines = [f"count={result.get('count', 0)}"]
        for w in result.get("windows") or []:
            lines.append(
                f"hwnd={w.get('hwnd')} pid={w.get('pid')} "
                f"process={w.get('process')!r} title={w.get('title')!r}"
            )
        return "\n".join(lines)

    return 5


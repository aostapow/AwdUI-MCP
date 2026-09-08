"""Target window auto-focus -- session state for multi-window workflows.

When a target window is set, input actions (click, type, keys, scroll,
drag, hover) may auto-focus that window before executing — controlled by
``focus_policy`` (default ``minimal``: only steal focus when pointer/keyboard
input requires it and the target is not already foreground).

Provides MCP tools:
    set_target_window  - set (or clear) the target window title + focus policy
    get_target_window  - return the current target window title and policy
"""

import sys
from typing import Literal, Optional

FocusPolicy = Literal["minimal", "always", "never"]

_target_window: Optional[str] = None
_target_hwnd: Optional[int] = None
_focus_policy: FocusPolicy = "minimal"
_last_focus_target: Optional[str] = None
_last_focus_time: float = 0.0

_VALID_POLICIES = frozenset({"minimal", "always", "never"})


def _normalize_policy(policy: Optional[str]) -> FocusPolicy:
    p = (policy or "minimal").strip().lower()
    if p in _VALID_POLICIES:
        return p  # type: ignore[return-value]
    return "minimal"


def _find_ancestor_window() -> bool:
    """Walk up the process tree and focus the first ancestor with a window.

    The MCP server is a child of the host terminal (e.g. Claude Code).
    By walking up PIDs we can find and focus the terminal without
    guessing window titles.  Returns True if successful.
    """
    if sys.platform == "win32":
        return _find_ancestor_window_win32()
    elif sys.platform == "darwin":
        return _find_ancestor_window_darwin()
    return False


def _find_ancestor_window_win32() -> bool:
    """Win32: walk parent PIDs, find one that owns a visible window."""
    try:
        import ctypes
        import ctypes.wintypes
        import os

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        GetWindowThreadProcessId = user32.GetWindowThreadProcessId
        IsWindowVisible = user32.IsWindowVisible
        GetWindowTextLengthW = user32.GetWindowTextLengthW
        EnumWindows = user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(
            ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
        )

        pid_to_hwnd: dict[int, int] = {}

        def _enum(hwnd, _lp):
            if IsWindowVisible(hwnd) and GetWindowTextLengthW(hwnd) > 0:
                pid = ctypes.wintypes.DWORD()
                GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value not in pid_to_hwnd:
                    pid_to_hwnd[pid.value] = hwnd
            return True

        EnumWindows(EnumWindowsProc(_enum), 0)

        pid = os.getpid()
        for _ in range(10):
            pid = _get_parent_pid_win32(pid)
            if pid is None or pid <= 0:
                break
            if pid in pid_to_hwnd:
                hwnd = pid_to_hwnd[pid]
                from tools.windows import do_focus_window
                SetForegroundWindow = user32.SetForegroundWindow
                ShowWindow = user32.ShowWindow
                BringWindowToTop = user32.BringWindowToTop
                GetForegroundWindow = user32.GetForegroundWindow
                AttachThreadInput = user32.AttachThreadInput
                GetCurrentThreadId = kernel32.GetCurrentThreadId

                fg_hwnd = GetForegroundWindow()
                fg_tid = GetWindowThreadProcessId(fg_hwnd, None)
                our_tid = GetCurrentThreadId()

                if fg_tid != our_tid:
                    AttachThreadInput(our_tid, fg_tid, True)

                ShowWindow(hwnd, 9)  # SW_RESTORE
                BringWindowToTop(hwnd)
                SetForegroundWindow(hwnd)

                if fg_tid != our_tid:
                    AttachThreadInput(our_tid, fg_tid, False)

                import time
                for _ in range(50):
                    time.sleep(0.01)
                    if GetForegroundWindow() == hwnd:
                        return True
                return True
    except Exception:
        pass
    return False


def _get_parent_pid_win32(pid: int):
    """Get parent PID using CreateToolhelp32Snapshot."""
    try:
        import ctypes
        import ctypes.wintypes

        TH32CS_SNAPPROCESS = 0x00000002

        class PROCESSENTRY32(ctypes.Structure):
            _fields_ = [
                ("dwSize", ctypes.wintypes.DWORD),
                ("cntUsage", ctypes.wintypes.DWORD),
                ("th32ProcessID", ctypes.wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", ctypes.wintypes.DWORD),
                ("cntThreads", ctypes.wintypes.DWORD),
                ("th32ParentProcessID", ctypes.wintypes.DWORD),
                ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", ctypes.wintypes.DWORD),
                ("szExeFile", ctypes.c_char * 260),
            ]

        kernel32 = ctypes.windll.kernel32
        snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if snapshot == -1:
            return None

        try:
            entry = PROCESSENTRY32()
            entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
            if not kernel32.Process32First(snapshot, ctypes.byref(entry)):
                return None
            while True:
                if entry.th32ProcessID == pid:
                    return entry.th32ParentProcessID
                if not kernel32.Process32Next(snapshot, ctypes.byref(entry)):
                    return None
        finally:
            kernel32.CloseHandle(snapshot)
    except Exception:
        return None


def _find_ancestor_window_darwin() -> bool:
    """macOS: walk parent PIDs, match against window-owning processes."""
    try:
        import os
        import subprocess

        pid = os.getpid()
        for _ in range(10):
            result = subprocess.run(
                ["ps", "-o", "ppid=", "-p", str(pid)],
                capture_output=True, text=True, timeout=2,
            )
            ppid_str = result.stdout.strip()
            if not ppid_str:
                break
            pid = int(ppid_str)
            if pid <= 1:
                break

            result = subprocess.run(
                ["ps", "-o", "comm=", "-p", str(pid)],
                capture_output=True, text=True, timeout=2,
            )
            comm = result.stdout.strip()
            if not comm:
                continue

            activate = subprocess.run(
                ["osascript", "-e",
                 f'tell application "System Events" to set frontmost '
                 f'of (first process whose unix id is {pid}) to true'],
                capture_output=True, timeout=3,
            )
            if activate.returncode == 0:
                return True
    except Exception:
        pass
    return False


def _refocus_host_terminal() -> None:
    """Bring the host terminal back to the foreground."""
    if _find_ancestor_window():
        return

    try:
        from tools.windows import do_focus_window
        if sys.platform == "darwin":
            for name in ("Terminal", "iTerm2", "Ghostty", "Alacritty", "kitty", "Warp"):
                result = do_focus_window(name, action="focus")
                if result.get("success"):
                    return
        else:
            import os
            title = os.environ.get("CLAUDE_TERMINAL_TITLE", "")
            if title:
                result = do_focus_window(title, action="focus")
                if result.get("success"):
                    return
            for name in ("Claude Code", "Windows Terminal", "PowerShell",
                         "Command Prompt", "cmd.exe"):
                result = do_focus_window(name, action="focus")
                if result.get("success"):
                    return
    except Exception:
        pass


def _prefetch_electron_treeitem_cache(
    window_title: Optional[str], window_handle: Optional[int]
) -> None:
    """Warm TreeItem list cache for Electron sidebars (background, non-blocking)."""
    if not window_title and not window_handle:
        return
    try:
        from tools.framework_detect import do_detect_framework

        fw = str(do_detect_framework(window_title).get("framework") or "")
        if fw not in ("electron", "chromium_browser"):
            return
    except Exception:
        return

    import threading

    title = window_title
    hwnd = int(window_handle or 0)

    def _run() -> None:
        try:
            from detection.orchestrator import get_orchestrator

            get_orchestrator().list_elements(
                window_title=title,
                max_depth=6,
                role="TreeItem",
                window_handle=hwnd or None,
            )
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True, name="awdui-prefetch-treeitem").start()


def set_target(title: Optional[str] = None, window_handle: Optional[int] = None) -> None:
    """Set (or clear) the target window for session scope."""
    global _target_window, _target_hwnd, _last_focus_target, _last_focus_time
    was_set = _target_window is not None or _target_hwnd is not None

    if title is not None and str(title).strip() == "":
        _target_window = None
        _target_hwnd = None
        _last_focus_target = None
        _last_focus_time = 0.0
        print("[target_window] Target cleared", file=sys.stderr)
        if was_set:
            _refocus_host_terminal()
        return

    resolved_title = (title or "").strip() or None
    resolved_hwnd: Optional[int] = None
    if window_handle is not None:
        try:
            hwnd = int(window_handle)
        except (TypeError, ValueError):
            hwnd = 0
        if hwnd > 0:
            resolved_hwnd = hwnd
            from tools.windows import resolve_window_by_hwnd

            win = resolve_window_by_hwnd(hwnd)
            if win:
                resolved_title = str(win.get("title") or resolved_title or "")

    _target_window = resolved_title or None
    _target_hwnd = resolved_hwnd
    _last_focus_target = None
    _last_focus_time = 0.0
    if _target_window or _target_hwnd:
        suffix = f" hwnd={_target_hwnd}" if _target_hwnd else ""
        print(f"[target_window] Target set: {_target_window!r}{suffix}", file=sys.stderr)
        _prefetch_electron_treeitem_cache(_target_window, _target_hwnd)
    elif title is None and window_handle is None:
        _target_window = None
        _target_hwnd = None
        print("[target_window] Target cleared", file=sys.stderr)
        if was_set:
            _refocus_host_terminal()


def get_target_hwnd() -> Optional[int]:
    """Return pinned HWND for session target, if any."""
    return _target_hwnd


def set_focus_policy(policy: Optional[str]) -> FocusPolicy:
    """Set session focus policy (minimal | always | never)."""
    global _focus_policy
    _focus_policy = _normalize_policy(policy)
    print(f"[target_window] focus_policy={_focus_policy}", file=sys.stderr)
    return _focus_policy


def get_target() -> Optional[str]:
    """Return the current target window title, or ``None``."""
    return _target_window


def get_focus_policy() -> FocusPolicy:
    return _focus_policy


def is_target_foreground() -> bool:
    """True when no target is set, or the target title matches the foreground window."""
    if _target_window is None:
        return True
    try:
        from tools.windows import get_foreground_title
        fg = (get_foreground_title() or "").lower()
        target = _target_window.lower()
        if not fg:
            return False
        return target in fg or fg in target
    except Exception:
        return False


def ensure_focus(force: bool = False) -> bool:
    """Focus the target window when policy allows.

    minimal (default): only focuses when ``force=True`` or policy is ``always``.
    never: never steals focus; returns whether target is already foreground.
    """
    if _target_window is None:
        return True
    if _focus_policy == "never":
        return is_target_foreground()
    if is_target_foreground():
        return True
    if _focus_policy == "minimal" and not force:
        return False

    import time
    from tools.perf import focus_cache_ttl
    global _last_focus_target, _last_focus_time
    now = time.monotonic()
    if (
        _last_focus_target == _target_window
        and now - _last_focus_time < focus_cache_ttl()
        and is_target_foreground()
    ):
        return True

    from tools.windows import do_focus_window
    do_focus_window(_target_window, action="focus")
    _last_focus_target = _target_window
    _last_focus_time = now
    return is_target_foreground()


def ensure_focus_for_input(*, skip_client_focus: Optional[bool] = None) -> bool:
    """Focus before pointer/keyboard input when the target is not already foreground."""
    if skip_client_focus is None:
        skip_client_focus = _focus_policy == "minimal"
    if _target_window is None:
        return True
    if _focus_policy == "never":
        return is_target_foreground()
    if not is_target_foreground():
        ensure_focus(force=True)
    if (
        not skip_client_focus
        and sys.platform == "win32"
        and _target_window
        and _focus_policy != "never"
    ):
        try:
            from tools.client_focus import ensure_client_focus

            ensure_client_focus()
        except Exception:
            pass
    return is_target_foreground()


def ensure_focus_for_capture() -> bool:
    """Optional focus before screenshot/OCR — skipped under minimal/never (crop by HWND)."""
    if _focus_policy == "always":
        return ensure_focus(force=True)
    return is_target_foreground()


def register(server) -> int:
    """Register the target-window tools on *server*. Returns 2."""

    @server.tool()
    def set_target_window(
        title: str = "",
        window_title: str = "",
        window_handle: int = 0,
        focus_policy: str = "",
        disambiguate: str = "error",
    ) -> str:
        """Set or clear the target window for session scope and optional focus policy.

        focus_policy (default **minimal**):
          minimal — UIA observe/act without stealing focus; focus only for
            pointer/keyboard input when the target is not already foreground.
          always — legacy: auto-focus target before input, screenshot, and on set.
          never — never steal focus; pointer/keyboard may fail if target is in background.

        window_handle — pin a specific top-level HWND (multi-instance Win32). When set,
        title is optional and resolved from list_windows.

        disambiguate — when multiple windows match the title hint (same process):
          error (default) — fail with candidate list; use window_handle or exact title.
          foreground — pick the foreground window among candidates.
          last_set — reuse previously pinned HWND if still among candidates.

        When cleared (empty title and window_handle=0), the host terminal is refocused.

        IMPORTANT: call set_target_window('') when done with GUI work.
        """
        from tools.params import resolve_window_title
        from tools.windows import do_list_windows, find_matching_window

        if focus_policy.strip():
            set_focus_policy(focus_policy)
        resolved = resolve_window_title(window_title, title)
        hwnd = int(window_handle or 0)

        if hwnd > 0:
            set_target(resolved, window_handle=hwnd)
        elif resolved:
            match = find_matching_window(
                resolved,
                do_list_windows(),
                disambiguate=disambiguate or "error",
                preferred_hwnd=get_target_hwnd(),
            )
            if match.get("ambiguous"):
                lines = [
                    f"Failed: ambiguous target for {resolved!r} — {match.get('hint', '')}",
                    "Candidates:",
                ]
                for cand in match.get("candidates") or []:
                    lines.append(
                        f"  hwnd={cand.get('hwnd')} pid={cand.get('pid')} "
                        f"title={cand.get('title')!r}"
                    )
                return "\n".join(lines)
            win = match.get("window")
            if not win:
                avail = match.get("available") or []
                preview = ", ".join(repr(t) for t in avail[:8])
                return f"Failed: no window matching {resolved!r}. Available: {preview}"
            set_target(win.get("title") or resolved, window_handle=win.get("hwnd"))
        else:
            set_target("")

        current = get_target()
        pinned = get_target_hwnd()
        policy = get_focus_policy()
        if current or pinned:
            if policy == "always":
                ensure_focus(force=True)
            hwnd_note = f" hwnd={pinned}" if pinned else ""
            msg = (
                f"Target window set to {current!r}{hwnd_note} (focus_policy={policy}). "
                "UIA tools work without foreground; pointer/keyboard focus only when needed. "
                "REMEMBER: call set_target_window('') when done."
            )
            return msg
        return "Target window cleared. Terminal refocused."

    @server.tool()
    def get_target_window() -> str:
        """Get the current target window and focus policy."""
        current = get_target()
        pinned = get_target_hwnd()
        policy = get_focus_policy()
        if current or pinned:
            fg = "foreground" if is_target_foreground() else "background"
            hwnd_note = f"  hwnd={pinned}" if pinned else ""
            title_note = current or "(hwnd only)"
            return f"Target window: {title_note!r}{hwnd_note}  focus_policy={policy}  ({fg})"
        return f"No target window set. focus_policy={policy}"

    return 2

"""Smart application launch — reuse existing windows, avoid duplicate instances."""
from __future__ import annotations

import os
import subprocess
import time
from typing import Any, Optional

from detection.uwp_window import is_uwp_shell_window


def launch_key(path: str) -> str:
    """Normalize ``calc.exe`` → ``calc`` for profile lookup."""
    base = os.path.basename(path).strip().lower()
    if "." in base:
        return base.rsplit(".", 1)[0]
    return base


def _process_matches_launch_key(proc: str, key: str) -> bool:
    proc_lower = (proc or "").lower()
    if not proc_lower or not key:
        return False
    stem = proc_lower.rsplit(".", 1)[0] if "." in proc_lower else proc_lower
    return stem == key or key in proc_lower


def _title_matches_launch_key(title: str, key: str) -> bool:
    title_lower = (title or "").lower()
    key_lower = (key or "").lower()
    if not title_lower or not key_lower:
        return False
    return key_lower in title_lower


def attach_uwp_shell_siblings(
    windows: list[dict],
    matches: list[dict],
) -> list[dict]:
    """Include ApplicationFrameHost windows that share a title with a core match."""
    if not matches:
        return matches
    titles = {(w.get("title") or "").strip().lower() for w in matches if w.get("title")}
    out = list(matches)
    seen = {int(w.get("hwnd") or 0) for w in out if w.get("hwnd")}
    for win in windows:
        hwnd = int(win.get("hwnd") or 0)
        if hwnd and hwnd in seen:
            continue
        if not is_uwp_shell_window(win):
            continue
        if (win.get("title") or "").strip().lower() in titles:
            out.append(win)
            if hwnd:
                seen.add(hwnd)
    return out


def match_app_windows(
    windows: list[dict],
    path: str,
    profile: Optional[dict[str, Any]] = None,
) -> list[dict]:
    """Return visible windows that belong to the app launched via *path*."""
    key = launch_key(path)
    matches: list[dict] = []

    for win in windows:
        proc = win.get("process_name") or ""
        title = win.get("title") or ""
        if not title and not proc:
            continue

        if _process_matches_launch_key(proc, key):
            matches.append(win)
            continue
        if _title_matches_launch_key(title, key):
            matches.append(win)

    return attach_uwp_shell_siblings(windows, matches)


def rank_app_window(win: dict, profile: Optional[dict[str, Any]] = None) -> int:
    """Higher score = better candidate to keep focused."""
    score = 0
    if is_uwp_shell_window(win):
        score -= 500
    else:
        score += 1000
    area = int(win.get("width", 0) or 0) * int(win.get("height", 0) or 0)
    score += area // 1000
    return score


def pick_primary_window(
    windows: list[dict],
    profile: Optional[dict[str, Any]] = None,
) -> Optional[dict]:
    if not windows:
        return None
    return max(windows, key=lambda w: rank_app_window(w, profile))


def collect_primary_pids(
    windows: list[dict],
    profile: Optional[dict[str, Any]] = None,
) -> set[int]:
    """PIDs to kill when closing extras (prefer app process, not UWP shell)."""
    pids: set[int] = set()
    core_windows = [w for w in windows if not is_uwp_shell_window(w)]
    targets = core_windows or windows
    for win in targets:
        hwnd = win.get("hwnd")
        if not hwnd:
            continue
        pids.add(get_window_pid(int(hwnd)))
    return pids


def kill_process_pid(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        result = subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def kill_process_names(names: tuple[str, ...] | list[str]) -> int:
    """Kill all processes matching *names*. Returns count of successful kills."""
    killed = 0
    for name in names:
        try:
            result = subprocess.run(
                ["taskkill", "/IM", name, "/F"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode == 0:
                killed += 1
        except (OSError, subprocess.TimeoutExpired):
            pass
    return killed


def verify_app_health(
    window_title: str,
    profile: Optional[dict[str, Any]] = None,
) -> bool:
    """Light UIA probe — optional sanity check after reuse."""
    aid = (profile or {}).get("health_automation_id")
    if not aid:
        return True
    try:
        from tools.ui_automation import do_find_element

        found = do_find_element(automation_id=aid, window_title=window_title)
        return bool(found.get("found"))
    except Exception:
        return True


def close_extra_instances(
    matches: list[dict],
    keep: dict,
    profile: Optional[dict[str, Any]] = None,
) -> int:
    """Close duplicate instances, keeping *keep*. Returns number closed."""
    keep_hwnd = int(keep.get("hwnd") or 0)
    keep_pid = get_window_pid(keep_hwnd) if keep_hwnd else 0
    all_pids = collect_primary_pids(matches, profile)
    closed = 0
    for pid in sorted(all_pids):
        if pid == keep_pid:
            continue
        if kill_process_pid(pid):
            closed += 1
    return closed


def kill_all_matched_instances(matches: list[dict]) -> int:
    """Kill every process backing *matches* (used for replace=true)."""
    closed = 0
    for pid in sorted(collect_primary_pids(matches)):
        if kill_process_pid(pid):
            closed += 1
    return closed


def try_reuse_existing(
    path: str,
    *,
    replace: bool = False,
) -> Optional[dict]:
    """Focus an existing instance or close extras. Returns result dict or None to spawn."""
    from tools.windows import do_focus_window, do_list_windows

    if replace:
        windows = do_list_windows()
        matches = match_app_windows(windows, path)
        if matches:
            kill_all_matched_instances(matches)
            time.sleep(0.6)
        return None

    windows = do_list_windows()
    matches = match_app_windows(windows, path)
    if not matches:
        return None

    primary = pick_primary_window(matches)
    if not primary:
        return None

    closed_extra = 0
    if len(matches) > 1 or len(collect_primary_pids(matches)) > 1:
        closed_extra = close_extra_instances(matches, primary)
        if closed_extra:
            time.sleep(0.4)
            windows = do_list_windows()
            matches = match_app_windows(windows, path)
            primary = pick_primary_window(matches) or primary

    title = (primary.get("title") or "").strip()
    if not title:
        return None

    focus = do_focus_window(title, action="focus")
    if not focus.get("success"):
        return None

    hwnd = int(primary.get("hwnd") or 0)
    pid = get_window_pid(hwnd) if hwnd else 0
    healthy = verify_app_health(title)

    try:
        from detection.orchestrator import invalidate_tree_cache

        invalidate_tree_cache(title)
    except Exception:
        pass

    return {
        "success": True,
        "pid": pid,
        "reused": True,
        "window_title": title,
        "closed_extra": closed_extra,
        "healthy": healthy,
        "action": "focused",
    }


def get_window_pid(hwnd: int) -> int:
    import ctypes
    import ctypes.wintypes

    pid = ctypes.wintypes.DWORD()
    ctypes.windll.user32.GetWindowThreadProcessId(int(hwnd), ctypes.byref(pid))
    return int(pid.value)

"""Smart application launch — reuse existing windows, avoid duplicate instances."""
from __future__ import annotations

import os
import subprocess
import time
from typing import Any, Optional

# Known apps with non-obvious process ↔ exe mapping (UWP, aliases).
LAUNCH_PROFILES: dict[str, dict[str, Any]] = {
    "calc": {
        "process_names": ("calculatorapp.exe",),
        "window_hints": ("calculadora", "calculator"),
        "kill_process_names": ("CalculatorApp.exe",),
        "health_automation_id": "num1Button",
    },
}


def launch_key(path: str) -> str:
    """Normalize ``calc.exe`` → ``calc`` for profile lookup."""
    base = os.path.basename(path).strip().lower()
    if "." in base:
        return base.rsplit(".", 1)[0]
    return base


def resolve_launch_profile(path: str) -> Optional[dict[str, Any]]:
    return LAUNCH_PROFILES.get(launch_key(path))


def get_window_pid(hwnd: int) -> int:
    import ctypes
    import ctypes.wintypes

    pid = ctypes.wintypes.DWORD()
    ctypes.windll.user32.GetWindowThreadProcessId(int(hwnd), ctypes.byref(pid))
    return int(pid.value)


def match_app_windows(
    windows: list[dict],
    path: str,
    profile: Optional[dict[str, Any]] = None,
) -> list[dict]:
    """Return visible windows that belong to the app launched via *path*."""
    profile = profile or resolve_launch_profile(path)
    key = launch_key(path)
    matches: list[dict] = []

    for win in windows:
        proc = (win.get("process_name") or "").lower()
        title = (win.get("title") or "").lower()
        if not title:
            continue

        if profile:
            proc_names = tuple(p.lower() for p in profile.get("process_names", ()))
            hints = tuple(h.lower() for h in profile.get("window_hints", ()))
            if proc_names and proc in proc_names:
                matches.append(win)
                continue
            if hints and any(h in title for h in hints):
                # UWP shell (ApplicationFrameHost) shares the calculator title.
                if proc_names and proc == "applicationframehost.exe":
                    matches.append(win)
                elif proc_names and proc in proc_names:
                    matches.append(win)
                elif not proc_names:
                    matches.append(win)
            continue

        stem = proc.rsplit(".", 1)[0] if proc else ""
        if stem == key or (proc and key in proc):
            matches.append(win)

    return matches


def rank_app_window(win: dict, profile: Optional[dict[str, Any]]) -> int:
    """Higher score = better candidate to keep focused."""
    proc = (win.get("process_name") or "").lower()
    score = 0
    if profile:
        for idx, name in enumerate(profile.get("process_names", ())):
            if name.lower() == proc:
                score += 1000 - idx
    area = int(win.get("width", 0) or 0) * int(win.get("height", 0) or 0)
    score += area // 1000
    return score


def pick_primary_window(
    windows: list[dict],
    profile: Optional[dict[str, Any]],
) -> Optional[dict]:
    if not windows:
        return None
    return max(windows, key=lambda w: rank_app_window(w, profile))


def collect_primary_pids(
    windows: list[dict],
    profile: Optional[dict[str, Any]],
) -> set[int]:
    """PIDs to kill when closing extras (prefer app process, not shell)."""
    pids: set[int] = set()
    proc_names = tuple(
        p.lower() for p in (profile or {}).get("process_names", ())
    )
    for win in windows:
        proc = (win.get("process_name") or "").lower()
        hwnd = win.get("hwnd")
        if not hwnd:
            continue
        if proc_names:
            if proc in proc_names:
                pids.add(get_window_pid(int(hwnd)))
        else:
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
    profile: Optional[dict[str, Any]],
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
    profile: Optional[dict[str, Any]],
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


def try_reuse_existing(
    path: str,
    *,
    replace: bool = False,
) -> Optional[dict]:
    """Focus an existing instance or close extras. Returns result dict or None to spawn."""
    from tools.windows import do_focus_window, do_list_windows

    profile = resolve_launch_profile(path)
    if replace and profile:
        names = profile.get("kill_process_names") or profile.get("process_names", ())
        if names:
            kill_process_names(tuple(names))
            time.sleep(0.6)
            return None

    windows = do_list_windows()
    matches = match_app_windows(windows, path, profile)
    if not matches:
        return None

    primary = pick_primary_window(matches, profile)
    if not primary:
        return None

    closed_extra = 0
    if len(matches) > 1 or len(collect_primary_pids(matches, profile)) > 1:
        closed_extra = close_extra_instances(matches, primary, profile)
        if closed_extra:
            time.sleep(0.4)
            windows = do_list_windows()
            matches = match_app_windows(windows, path, profile)
            primary = pick_primary_window(matches, profile) or primary

    title = (primary.get("title") or "").strip()
    if not title:
        return None

    focus = do_focus_window(title, action="focus")
    if not focus.get("success"):
        return None

    hwnd = int(primary.get("hwnd") or 0)
    pid = get_window_pid(hwnd) if hwnd else 0
    healthy = verify_app_health(title, profile)

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

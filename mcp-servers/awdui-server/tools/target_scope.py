"""Enforce MCP input/UIA actions stay within the session target window."""
from __future__ import annotations

from typing import Any, Optional


def _pid(win: dict[str, Any]) -> int:
    return int(win.get("process_id") or win.get("pid") or 0)


def get_scoped_windows() -> Optional[list[dict[str, Any]]]:
    """Return top-level windows matching the current session target, or None if unset."""
    from tools.target_window import get_target
    from tools.windows import do_list_windows, find_matching_window

    title = (get_target() or "").strip()
    if not title:
        return None

    title_lower = title.lower()
    windows = do_list_windows()
    candidates = [
        w for w in windows if title_lower in (w.get("title") or "").lower()
    ]
    if not candidates:
        match = find_matching_window(title, windows)
        if match.get("window"):
            candidates = [match["window"]]
    return candidates or []


def get_target_process_ids() -> Optional[set[int]]:
    """PIDs allowed for scoped actions; None when no target is set."""
    windows = get_scoped_windows()
    if windows is None:
        return None
    pids = {_pid(w) for w in windows}
    pids.discard(0)
    return pids


def _window_bounds(win: dict[str, Any]) -> tuple[int, int, int, int]:
    x = int(win.get("x", 0) or 0)
    y = int(win.get("y", 0) or 0)
    w = int(win.get("width", 0) or 0)
    h = int(win.get("height", 0) or 0)
    return x, y, x + w, y + h


def validate_point_in_scope(x: int, y: int) -> tuple[bool, str]:
    """True when (*x*, *y*) lies inside a scoped target window outer rect."""
    from tools.target_window import get_target

    if not (get_target() or "").strip():
        return True, ""

    windows = get_scoped_windows() or []
    if not windows:
        return False, "blocked: no window matches session target"

    for win in windows:
        x0, y0, x1, y1 = _window_bounds(win)
        if x0 <= x <= x1 and y0 <= y <= y1:
            return True, ""
    return False, "blocked: coordinate outside target window scope"


def validate_element_in_scope(elem: dict[str, Any]) -> tuple[bool, str]:
    """True when element PID and center point belong to the session target."""
    from tools.target_window import get_target

    if not (get_target() or "").strip():
        return True, ""

    pids = get_target_process_ids()
    if pids is None:
        return True, ""

    ep = int(elem.get("process_id") or elem.get("pid") or 0)
    if ep and ep not in pids:
        return False, f"blocked: element process {ep} outside target scope"

    cx = int(elem.get("x", 0) or 0) + int(elem.get("width", 0) or 0) // 2
    cy = int(elem.get("y", 0) or 0) + int(elem.get("height", 0) or 0) // 2
    return validate_point_in_scope(cx, cy)

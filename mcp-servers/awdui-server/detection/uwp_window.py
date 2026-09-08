"""Generic UWP shell vs core window heuristics (ApplicationFrameHost pairing)."""
from __future__ import annotations


def is_uwp_shell_window(win: dict) -> bool:
    """True when *win* is the visible host frame around a UWP CoreWindow."""
    proc = (win.get("process_name") or "").lower()
    cls = (win.get("class_name") or "").lower()
    return "applicationframehost" in proc or "applicationframewindow" in cls


def uwp_window_score_bonus(win: dict, *, purpose: str) -> int:
    """Extra score for UWP disambiguation when several HWNDs share a title."""
    if not is_uwp_shell_window(win):
        if purpose == "handle":
            return 12000
        return 5000
    if purpose == "visual":
        return 12000
    return 8000

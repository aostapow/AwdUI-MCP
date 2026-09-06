"""Resolve automation window scope (target + modal / MDI children)."""
from __future__ import annotations

from typing import Any, Optional


def resolve_window_scope(window_title: Optional[str] = None) -> dict[str, Any]:
    from tools.target_window import get_target
    from tools.windows import do_list_windows, find_matching_window

    requested = (window_title or "").strip()
    title = requested or (get_target() or "").strip()
    windows = do_list_windows()

    if not title:
        return {
            "requested_title": requested,
            "resolved_title": "",
            "has_target": False,
            "scoped": "none",
            "window": None,
        }

    direct = find_matching_window(title, windows)
    if direct.get("window"):
        return {
            "requested_title": requested,
            "resolved_title": title,
            "has_target": True,
            "scoped": "direct",
            "window": direct["window"],
            "match_quality": direct.get("match_quality", "exact"),
        }

    target = (get_target() or "").strip()
    parent = None
    parent_title = ""
    parent_pid = None
    if target:
        parent_match = find_matching_window(target, windows)
        parent = parent_match.get("window")
        if parent:
            parent_title = parent.get("title") or target
            parent_pid = parent.get("process_id")

    title_lower = title.lower()
    for win in windows:
        win_title = win.get("title") or ""
        if title_lower not in win_title.lower():
            continue
        if parent_pid is not None and win.get("process_id") == parent_pid:
            return {
                "requested_title": requested,
                "resolved_title": title,
                "has_target": True,
                "scoped": "mdi_child",
                "window": win,
                "parent_title": parent_title,
            }

    return {
        "requested_title": requested,
        "resolved_title": title,
        "has_target": bool(target or requested),
        "scoped": "not_found",
        "window": None,
        "available": direct.get("available", []),
    }

"""Shared element resolution for actions (exact + fuzzy, WinApp index rules)."""
from __future__ import annotations

from typing import Any, Optional

from tools.app_session import pick_element_index


def find_element_for_action(
    automation_id: Optional[str] = None,
    name: Optional[str] = None,
    role: Optional[str] = None,
    index: int = -1,
    window_title: Optional[str] = None,
    window_handle: Optional[int] = None,
    fuzzy_match: bool = False,
) -> tuple[Optional[dict[str, Any]], Optional[dict[str, Any]]]:
    """Return (element_dict, error_dict)."""
    if fuzzy_match and (name or automation_id):
        from detection.fuzzy_match import fuzzy_match_elements
        from tools.ui_automation import do_list_elements

        listing = do_list_elements(
            window_title=window_title,
            window_handle=window_handle,
            max_depth=8,
            role=role or None,
            include_offscreen=False,
        )
        matched = fuzzy_match_elements(
            listing.get("elements") or [],
            name or automation_id or "",
            max_results=max(5, pick_element_index(index, 5) + 1),
        )
        if not matched:
            return None, {"success": False, "error": "Element not found (fuzzy)"}
        return matched[pick_element_index(index, len(matched))], None

    from tools.ui_automation import do_find_element

    found = do_find_element(
        automation_id=automation_id,
        name=name,
        role=role,
        window_title=window_title,
        window_handle=window_handle,
        index=index,
        remember=False,
    )
    if not found.get("found") or not found.get("elements"):
        return None, {"success": False, "error": "Element not found"}
    idx = pick_element_index(index, len(found["elements"]))
    return found["elements"][idx], None

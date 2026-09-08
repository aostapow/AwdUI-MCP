"""Tab and radio interaction."""
from __future__ import annotations

from typing import Any, Optional


def select_tab(
    tab_control: str = "MhTab1",
    index: int = 0,
    caption: str = "",
    window_title: Optional[str] = None,
) -> dict[str, Any]:
    from tools.ui_automation import do_click_element, do_list_elements

    if caption:
        listed = do_list_elements(window_title=window_title or "", max_depth=6)
        if isinstance(listed, str):
            import json
            listed = json.loads(listed)
        for el in listed.get("elements") or []:
            if caption.lower() in (el.get("name") or "").lower():
                return do_click_element(
                    automation_id=el.get("automation_id") or "",
                    name=el.get("name") or "",
                    window_title=window_title or "",
                )

    tab_id = tab_control
    if index >= 0:
        tab_id = f"{tab_control}.{index}" if "." not in tab_control else tab_control
    return do_click_element(automation_id=tab_control, window_title=window_title or "")


def select_radio(
    group_prefix: str = "optVigente",
    index: int = 0,
    caption: str = "",
    window_title: Optional[str] = None,
) -> dict[str, Any]:
    from tools.ui_automation import do_click_element, do_find_element

    candidates = [
        f"_{group_prefix}_{index}",
        f"{group_prefix}[{index}]",
        group_prefix,
    ]
    if caption:
        found = do_find_element(name=caption, window_title=window_title or "")
        if isinstance(found, dict) and found.get("found"):
            return do_click_element(name=caption, window_title=window_title or "")

    for aid in candidates:
        result = do_click_element(automation_id=aid, window_title=window_title or "")
        if isinstance(result, dict) and result.get("success"):
            return {"success": True, "automation_id": aid, "result": result}
    return {"success": False, "error": f"Radio not found: {group_prefix}[{index}]"}

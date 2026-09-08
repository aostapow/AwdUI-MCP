"""MCP wrappers for advanced UIA patterns (scroll, virtualized lists, item lookup)."""
from __future__ import annotations

import sys
from typing import Any, Optional

from tools.control_items import _resolve_control


def _scope_title(scope: dict, window_title: Optional[str]) -> str:
    return scope.get("resolved_title") or window_title or ""


def _resolve_raw_control(
    automation_id: Optional[str] = None,
    name: Optional[str] = None,
    role: Optional[str] = None,
    index: int = -1,
    window_title: Optional[str] = None,
    window_handle: Optional[int] = None,
) -> tuple[Optional[object], Optional[dict[str, Any]], Optional[str], dict[str, Any]]:
    """Resolve a UIA raw control by automation_id or by name/role/index."""
    aid = (automation_id or "").strip()
    if aid:
        raw, _elem, data, scope = _resolve_control(aid, window_title)
        return raw, data, aid, scope

    if not (name or role):
        return None, None, None, {}

    from tools.ui_automation import do_find_element

    found = do_find_element(
        name=name,
        role=role,
        window_title=window_title,
        window_handle=window_handle,
        index=index,
        remember=False,
    )
    if not found.get("found") or not found.get("elements"):
        return None, None, None, {}

    from tools.app_session import pick_element_index

    elem = found["elements"][pick_element_index(index, len(found["elements"]))]
    resolved_aid = str(elem.get("automation_id") or "").strip()
    if not resolved_aid:
        return None, elem, None, {}
    raw, _elem, data, scope = _resolve_control(resolved_aid, window_title)
    return raw, data or elem, resolved_aid, scope


def do_scroll_into_view(
    automation_id: str = "",
    name: Optional[str] = None,
    role: Optional[str] = None,
    index: int = -1,
    window_title: Optional[str] = None,
    window_handle: Optional[int] = None,
) -> dict[str, Any]:
    if sys.platform != "win32":
        return {"success": False, "error": "scroll_into_view is Windows-only"}
    raw, data, resolved_aid, scope = _resolve_raw_control(
        automation_id=automation_id or None,
        name=name,
        role=role,
        index=index,
        window_title=window_title,
        window_handle=window_handle,
    )
    if not raw:
        label = automation_id or name or role or "element"
        return {"success": False, "error": f"Control not found: {label}"}

    from detection.uia_patterns import scroll_item_into_view

    result = scroll_item_into_view(raw)
    if resolved_aid:
        result["automation_id"] = resolved_aid
    elif data:
        result["name"] = data.get("name", "")
    result["resolved_window_title"] = _scope_title(scope, window_title)
    return result


def do_realize_virtualized_item(
    automation_id: str = "",
    name: Optional[str] = None,
    role: Optional[str] = None,
    index: int = -1,
    window_title: Optional[str] = None,
    window_handle: Optional[int] = None,
) -> dict[str, Any]:
    if sys.platform != "win32":
        return {"success": False, "error": "realize_virtualized_item is Windows-only"}
    raw, data, resolved_aid, scope = _resolve_raw_control(
        automation_id=automation_id or None,
        name=name,
        role=role,
        index=index,
        window_title=window_title,
        window_handle=window_handle,
    )
    if not raw:
        label = automation_id or name or role or "element"
        return {"success": False, "error": f"Control not found: {label}"}

    from detection.uia_patterns import realize_virtualized_item

    result = realize_virtualized_item(raw)
    if resolved_aid:
        result["automation_id"] = resolved_aid
    elif data:
        result["name"] = data.get("name", "")
    result["resolved_window_title"] = _scope_title(scope, window_title)
    return result


def do_find_item_by_property(
    container_automation_id: str,
    property_name: str,
    property_value: str,
    start_after_automation_id: str = "",
    window_title: Optional[str] = None,
) -> dict[str, Any]:
    if sys.platform != "win32":
        return {"success": False, "error": "find_item_by_property is Windows-only"}
    if not (container_automation_id or "").strip():
        return {"success": False, "error": "container_automation_id is required"}
    if not (property_name or "").strip():
        return {"success": False, "error": "property_name is required"}
    if not (property_value or "").strip():
        return {"success": False, "error": "property_value is required"}

    raw, _elem, _data, scope = _resolve_control(container_automation_id, window_title)
    if not raw:
        return {
            "success": False,
            "error": f"Container not found: {container_automation_id}",
        }

    start_after_raw = None
    if (start_after_automation_id or "").strip():
        start_after_raw, _, _, _ = _resolve_control(start_after_automation_id, window_title)

    from detection.uia_patterns import find_item_by_property

    result = find_item_by_property(
        raw,
        property_name,
        property_value,
        start_after_raw=start_after_raw,
    )
    result["container_automation_id"] = container_automation_id
    result["resolved_window_title"] = _scope_title(scope, window_title)
    return result


def do_scroll_element(
    automation_id: str = "",
    direction: str = "down",
    amount: str = "large",
    repeat: int = 1,
    clicks: int = 0,
    horizontal_percent: float = -1.0,
    vertical_percent: float = -1.0,
    window_title: Optional[str] = None,
    name: Optional[str] = None,
    role: Optional[str] = None,
    index: int = -1,
    window_handle: Optional[int] = None,
) -> dict[str, Any]:
    if sys.platform != "win32":
        return {"success": False, "error": "scroll_element is Windows-only"}
    if clicks and int(clicks) > 0:
        repeat = int(clicks)

    raw, data, resolved_aid, scope = _resolve_raw_control(
        automation_id=automation_id or None,
        name=name,
        role=role,
        index=index,
        window_title=window_title,
        window_handle=window_handle,
    )
    if not raw:
        label = automation_id or name or role or "element"
        return {"success": False, "error": f"Control not found: {label}"}

    from detection.uia_patterns import apply_scroll_pattern, find_scrollable_ancestor, _has_pattern

    h_pct = horizontal_percent if horizontal_percent >= 0 else None
    v_pct = vertical_percent if vertical_percent >= 0 else None
    scroll_raw = raw
    scroll_via = "self"
    if not _has_pattern(raw, "Scroll"):
        ancestor = find_scrollable_ancestor(raw)
        if ancestor is not None:
            scroll_raw = ancestor
            scroll_via = "ancestor"
    result = apply_scroll_pattern(
        scroll_raw,
        direction=direction,
        amount=amount,
        repeat=repeat,
        horizontal_percent=h_pct,
        vertical_percent=v_pct,
    )
    if result.get("success") and scroll_via == "ancestor":
        result["scroll_via"] = "ancestor"
    if not result.get("success"):
        from detection.uia_patterns import _element_dict

        elem = _element_dict(raw) if raw else {}
        ex = int(elem.get("x") or 0)
        ey = int(elem.get("y") or 0)
        ew = int(elem.get("width") or 0)
        eh = int(elem.get("height") or 0)
        if ew > 0 and eh > 0:
            cx, cy = ex + ew // 2, ey + eh // 2
            pages = 1.0 if str(amount).lower() in ("large", "page", "1") else 0.25
            from tools.input_tools import do_scroll

            fb = do_scroll(cx, cy, direction=direction or "down", pages=pages)
            if fb.get("action") == "scroll":
                result = {
                    "success": True,
                    "method": "scroll_fallback_coords",
                    "fallback_reason": result.get("error", "ScrollPattern failed"),
                    "x": cx,
                    "y": cy,
                    "direction": direction or "down",
                    "pages": pages,
                    "verified": fb.get("verified"),
                }
    if resolved_aid:
        result["automation_id"] = resolved_aid
    elif data:
        result["name"] = data.get("name", "")
    result["resolved_window_title"] = _scope_title(scope, window_title)
    return result

"""MCP wrappers for advanced UIA patterns (scroll, virtualized lists, item lookup)."""
from __future__ import annotations

import sys
from typing import Any, Optional

from tools.control_items import _resolve_control


def _scope_title(scope: dict, window_title: Optional[str]) -> str:
    return scope.get("resolved_title") or window_title or ""


def do_scroll_into_view(
    automation_id: str,
    window_title: Optional[str] = None,
) -> dict[str, Any]:
    if sys.platform != "win32":
        return {"success": False, "error": "scroll_into_view is Windows-only"}
    if not (automation_id or "").strip():
        return {"success": False, "error": "automation_id is required"}

    raw, _elem, _data, scope = _resolve_control(automation_id, window_title)
    if not raw:
        return {"success": False, "error": f"Control not found: {automation_id}"}

    from detection.uia_patterns import scroll_item_into_view

    result = scroll_item_into_view(raw)
    result["automation_id"] = automation_id
    result["resolved_window_title"] = _scope_title(scope, window_title)
    return result


def do_realize_virtualized_item(
    automation_id: str,
    window_title: Optional[str] = None,
) -> dict[str, Any]:
    if sys.platform != "win32":
        return {"success": False, "error": "realize_virtualized_item is Windows-only"}
    if not (automation_id or "").strip():
        return {"success": False, "error": "automation_id is required"}

    raw, _elem, _data, scope = _resolve_control(automation_id, window_title)
    if not raw:
        return {"success": False, "error": f"Control not found: {automation_id}"}

    from detection.uia_patterns import realize_virtualized_item

    result = realize_virtualized_item(raw)
    result["automation_id"] = automation_id
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
        start_after_raw, _, _, _ = _resolve_control(
            start_after_automation_id.strip(),
            window_title,
        )

    from detection.uia_patterns import find_item_by_property

    result = find_item_by_property(
        raw,
        property_name=property_name,
        value=property_value,
        start_after_raw=start_after_raw,
    )
    result["container_automation_id"] = container_automation_id
    result["resolved_window_title"] = _scope_title(scope, window_title)
    return result


def do_scroll_element(
    automation_id: str,
    direction: str = "down",
    amount: str = "large",
    repeat: int = 1,
    horizontal_percent: float = -1.0,
    vertical_percent: float = -1.0,
    window_title: Optional[str] = None,
) -> dict[str, Any]:
    if sys.platform != "win32":
        return {"success": False, "error": "scroll_element is Windows-only"}
    if not (automation_id or "").strip():
        return {"success": False, "error": "automation_id is required"}

    raw, _elem, _data, scope = _resolve_control(automation_id, window_title)
    if not raw:
        return {"success": False, "error": f"Control not found: {automation_id}"}

    from detection.uia_patterns import apply_scroll_pattern

    h_pct = horizontal_percent if horizontal_percent >= 0 else None
    v_pct = vertical_percent if vertical_percent >= 0 else None
    result = apply_scroll_pattern(
        raw,
        direction=direction,
        amount=amount,
        repeat=repeat,
        horizontal_percent=h_pct,
        vertical_percent=v_pct,
    )
    result["automation_id"] = automation_id
    result["resolved_window_title"] = _scope_title(scope, window_title)
    return result

"""Read editable field values from a form subtree."""
from __future__ import annotations

from typing import Any, Optional

_EDITABLE_ROLES = frozenset(
    {
        "Edit",
        "ComboBox",
        "CheckBox",
        "Spinner",
        "Document",
        "RadioButton",
    }
)


def _field_key(elem: dict[str, Any]) -> str:
    aid = (elem.get("automation_id") or "").strip()
    if aid:
        return aid
    return (elem.get("name") or "").strip()


def _read_value(elem: dict[str, Any]) -> str:
    role = (elem.get("role") or "").strip()
    value = (elem.get("value") or "").strip()
    if value:
        return value
    patterns = elem.get("patterns") or {}
    if isinstance(patterns, dict):
        toggle = patterns.get("Toggle") or {}
        if isinstance(toggle, dict) and toggle.get("toggle_state"):
            return str(toggle.get("toggle_state"))
    if role == "CheckBox":
        name = (elem.get("name") or "").lower()
        if "check" in name or name in ("on", "off"):
            return elem.get("name") or ""
    return elem.get("name") or ""


def collect_all_values(
    elements: list[dict[str, Any]],
) -> dict[str, Any]:
    values: dict[str, dict[str, Any]] = {}
    for elem in elements:
        role = (elem.get("role") or "").strip()
        if role not in _EDITABLE_ROLES:
            continue
        key = _field_key(elem)
        if not key:
            continue
        if key in values:
            suffix = f"#{elem.get('y', 0)}"
            key = f"{key}{suffix}"
        values[key] = {
            "automation_id": elem.get("automation_id") or "",
            "name": elem.get("name") or "",
            "role": role,
            "value": _read_value(elem),
        }
    return {
        "values": values,
        "count": len(values),
    }


def get_all_values(
    window_title: Optional[str] = None,
    window_handle: Optional[int] = None,
    max_depth: int = 12,
) -> dict[str, Any]:
    from tools.ui_automation import do_list_elements

    listing = do_list_elements(
        window_title=window_title,
        max_depth=max_depth,
        include_offscreen=False,
        window_handle=window_handle,
    )
    payload = collect_all_values(listing.get("elements") or [])
    payload["element_count"] = listing.get("count", 0)
    payload["backend_used"] = listing.get("backend_used", "")
    return payload

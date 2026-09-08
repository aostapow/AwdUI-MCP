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
    name = (elem.get("name") or "").strip()
    value = (elem.get("value") or "").strip()
    patterns = elem.get("patterns") or {}
    if isinstance(patterns, dict):
        val_pat = patterns.get("Value") or {}
        if isinstance(val_pat, dict):
            pattern_value = (val_pat.get("value") or "").strip()
            if pattern_value:
                return pattern_value
        toggle = patterns.get("Toggle") or {}
        if isinstance(toggle, dict) and toggle.get("toggle_state"):
            return str(toggle.get("toggle_state"))
    if value and not (role in ("Document", "Edit") and value == name):
        return value
    if role == "CheckBox":
        lname = name.lower()
        if "check" in lname or lname in ("on", "off"):
            return name
    if role in ("Document", "Edit"):
        return ""
    return name


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
    scope_mode: str = "auto",
) -> dict[str, Any]:
    from tools.ui_automation import do_list_elements
    from tools.window_scope import resolve_form_read_scope

    scope = resolve_form_read_scope(
        window_title=window_title,
        window_handle=window_handle,
        scope_mode=scope_mode,
    )
    wt = scope.get("window_title")
    hwnd = scope.get("window_handle")

    elements: list[dict[str, Any]] = []
    seen: set[tuple] = set()
    backend_used = ""
    for role in sorted(_EDITABLE_ROLES):
        listing = do_list_elements(
            window_title=wt,
            max_depth=max_depth,
            role=role,
            include_offscreen=False,
            window_handle=hwnd,
        )
        if not backend_used:
            backend_used = listing.get("backend_used", "") or ""
        for elem in listing.get("elements") or []:
            sig = (
                elem.get("automation_id"),
                elem.get("name"),
                elem.get("role"),
                elem.get("x"),
                elem.get("y"),
            )
            if sig in seen:
                continue
            seen.add(sig)
            elements.append(elem)

    payload = collect_all_values(elements)
    payload["element_count"] = len(elements)
    payload["backend_used"] = backend_used
    payload["scope"] = scope.get("scope", "target")
    if scope.get("modal_class"):
        payload["modal_class"] = scope["modal_class"]
    if scope.get("parent_title"):
        payload["parent_title"] = scope["parent_title"]
    return payload

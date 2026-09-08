"""UIA pattern helpers — Scroll, ScrollItem, VirtualizedItem, ItemContainer, Toggle, etc."""
from __future__ import annotations

from typing import Any, Optional

# UIA ScrollAmount (UIAutomationClient.h)
_SCROLL_NO = 0
_SCROLL_LARGE_DEC = 1
_SCROLL_SMALL_DEC = 2
_SCROLL_LARGE_INC = 3
_SCROLL_SMALL_INC = 4

# UIA property IDs for ItemContainer.FindItemByProperty
_UIA_PROPERTY_IDS: dict[str, int] = {
    "name": 30005,
    "automationid": 30011,
    "automation_id": 30011,
    "controltype": 30003,
    "localizedcontroltype": 30004,
    "classname": 30012,
}

_SUPPORTED_PATTERNS = (
    "Invoke",
    "Toggle",
    "SelectionItem",
    "ExpandCollapse",
    "Value",
    "Scroll",
    "ScrollItem",
    "VirtualizedItem",
    "ItemContainer",
    "Selection",
    "RangeValue",
    "Grid",
    "Table",
)

_TOGGLE_LABELS = {0: "off", 1: "on", 2: "indeterminate"}


def _element_iface(raw) -> Any:
    return raw.element_info.element


def _iface(raw, pattern_name: str):
    from pywinauto.uia_defines import get_elem_interface

    return get_elem_interface(_element_iface(raw), pattern_name)


def _has_pattern(raw, pattern_name: str) -> bool:
    try:
        _iface(raw, pattern_name)
        return True
    except Exception:
        return False


def _wrap_com_element(com_elem) -> Optional[object]:
    if com_elem is None:
        return None
    try:
        from pywinauto.controls.uiawrapper import UIAWrapper
        from pywinauto.uia_element_info import UIAElementInfo

        if hasattr(com_elem, "element_info"):
            return com_elem
        info = UIAElementInfo(com_elem)
        return UIAWrapper(info)
    except Exception:
        return None


def _element_dict(raw) -> dict[str, Any]:
    from detection.backends.uia_backend import _pywinauto_to_element

    det = _pywinauto_to_element(raw)
    if not det:
        return {}
    return det.to_dict()


def list_available_patterns(raw) -> list[str]:
    return [name for name in _SUPPORTED_PATTERNS if _has_pattern(raw, name)]


def read_pattern_state(raw, pattern_name: str) -> dict[str, Any]:
    if not _has_pattern(raw, pattern_name):
        return {"available": False, "pattern": pattern_name}
    pat = _iface(raw, pattern_name)
    state: dict[str, Any] = {"available": True, "pattern": pattern_name}
    try:
        if pattern_name == "Toggle":
            ts = pat.CurrentToggleState
            state["toggle_state"] = _TOGGLE_LABELS.get(ts, str(ts))
        elif pattern_name == "ExpandCollapse":
            state["expand_state"] = str(pat.CurrentExpandCollapseState)
        elif pattern_name == "Scroll":
            state.update(
                {
                    "horizontally_scrollable": bool(pat.CurrentHorizontallyScrollable),
                    "vertically_scrollable": bool(pat.CurrentVerticallyScrollable),
                    "horizontal_scroll_percent": float(pat.CurrentHorizontalScrollPercent),
                    "vertical_scroll_percent": float(pat.CurrentVerticalScrollPercent),
                }
            )
        elif pattern_name == "Value":
            state["value"] = pat.CurrentValue or ""
            state["is_read_only"] = bool(pat.CurrentIsReadOnly)
    except Exception as exc:
        state["read_error"] = str(exc)
    return state


def read_control_state(raw) -> dict[str, Any]:
    patterns = list_available_patterns(raw)
    states: dict[str, Any] = {}
    for pattern_name in patterns:
        ps = read_pattern_state(raw, pattern_name)
        if ps.get("available"):
            states[pattern_name] = {
                k: v for k, v in ps.items() if k not in ("available", "pattern")
            }
    return {"patterns": patterns, "states": states}


def _scroll_amount_code(amount: str, increment: bool = True) -> int:
    text = (amount or "large").strip().lower()
    if increment:
        if text in ("small", "small_increment"):
            return _SCROLL_SMALL_INC
        return _SCROLL_LARGE_INC
    if text in ("small", "small_decrement"):
        return _SCROLL_SMALL_DEC
    return _SCROLL_LARGE_DEC


def find_scrollable_ancestor(raw, max_levels: int = 12):
    """Walk UIA parents until a node supports ScrollPattern with scrollable axis."""
    current = raw
    for _ in range(max(1, int(max_levels))):
        if _has_pattern(current, "Scroll"):
            state = read_pattern_state(current, "Scroll")
            if state.get("horizontally_scrollable") or state.get("vertically_scrollable"):
                return current
            if state.get("available"):
                return current
        try:
            parent = current.parent()
            if parent is None or parent == current:
                break
            current = parent
        except Exception:
            break
    return None


def apply_scroll_pattern(
    raw,
    direction: Optional[str] = None,
    amount: str = "large",
    repeat: int = 1,
    horizontal_percent: Optional[float] = None,
    vertical_percent: Optional[float] = None,
) -> dict[str, Any]:
    """Scroll a scrollable container via ScrollPattern."""
    if not _has_pattern(raw, "Scroll"):
        return {"success": False, "error": "Scroll pattern not supported"}
    pat = _iface(raw, "Scroll")
    try:
        if horizontal_percent is not None or vertical_percent is not None:
            h = float(horizontal_percent if horizontal_percent is not None else -1.0)
            v = float(vertical_percent if vertical_percent is not None else -1.0)
            pat.SetScrollPercent(h, v)
            return {
                "success": True,
                "method": "Scroll.SetScrollPercent",
                "horizontal_percent": h,
                "vertical_percent": v,
            }

        dir_norm = (direction or "down").strip().lower()
        times = max(1, int(repeat or 1))
        calls: list[tuple[int, int]] = []
        for _ in range(times):
            if dir_norm in ("down", "vertical", "page_down"):
                code = _scroll_amount_code(amount, increment=True)
                pat.Scroll(_SCROLL_NO, code)
                calls.append((_SCROLL_NO, code))
            elif dir_norm in ("up", "page_up"):
                code = _scroll_amount_code(amount, increment=False)
                pat.Scroll(_SCROLL_NO, code)
                calls.append((_SCROLL_NO, code))
            elif dir_norm in ("right", "horizontal"):
                code = _scroll_amount_code(amount, increment=True)
                pat.Scroll(code, _SCROLL_NO)
                calls.append((code, _SCROLL_NO))
            elif dir_norm == "left":
                code = _scroll_amount_code(amount, increment=False)
                pat.Scroll(code, _SCROLL_NO)
                calls.append((code, _SCROLL_NO))
            else:
                return {"success": False, "error": f"Unknown scroll direction: {direction}"}
        return {
            "success": True,
            "method": "Scroll.Scroll",
            "direction": dir_norm,
            "amount": amount,
            "repeat": times,
            "calls": calls,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def scroll_item_into_view(raw) -> dict[str, Any]:
    """Bring an item into view via ScrollItemPattern."""
    if not _has_pattern(raw, "ScrollItem"):
        return {"success": False, "error": "ScrollItem pattern not supported"}
    try:
        _iface(raw, "ScrollItem").ScrollIntoView()
        payload = _element_dict(raw)
        return {
            "success": True,
            "method": "ScrollItem.ScrollIntoView",
            **payload,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def realize_virtualized_item(raw) -> dict[str, Any]:
    """Materialize a virtualized list item via VirtualizedItemPattern."""
    if not _has_pattern(raw, "VirtualizedItem"):
        return {"success": False, "error": "VirtualizedItem pattern not supported"}
    try:
        realized = _iface(raw, "VirtualizedItem").Realize()
        wrapper = _wrap_com_element(realized) or raw
        payload = _element_dict(wrapper)
        return {
            "success": True,
            "method": "VirtualizedItem.Realize",
            **payload,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _norm_property_name(name: str) -> str:
    return (name or "").strip().lower().replace(" ", "").replace("-", "_")


def _fallback_find_item(
    container_raw,
    property_name: str,
    value: str,
    start_after_raw: Optional[object] = None,
) -> tuple[Optional[object], Optional[dict[str, Any]]]:
    from detection.backends.uia_backend import _pywinauto_to_element
    from detection.uia_find import _list_item_nodes

    prop_key = _norm_property_name(property_name)
    if prop_key in ("automationid", "automation_id"):
        field = "automation_id"
        match_mode = "exact"
    else:
        field = "name"
        match_mode = "contains"

    needle = (value or "").strip()
    if not needle:
        return None, None

    start_idx = -1
    if start_after_raw is not None:
        start_det = _pywinauto_to_element(start_after_raw)
        start_aid = (getattr(start_det, "automation_id", "") or "").strip()
        start_name = (getattr(start_det, "name", "") or "").strip()
        nodes = _list_item_nodes(container_raw)
        for idx, node in enumerate(nodes):
            if start_aid and node.get("automation_id") == start_aid:
                start_idx = idx
                break
            if start_name and node.get("name") == start_name:
                start_idx = idx
                break

    nodes = _list_item_nodes(container_raw)
    for idx, node in enumerate(nodes):
        if idx <= start_idx:
            continue
        candidate = (node.get(field) or "").strip()
        if not candidate:
            continue
        if match_mode == "exact" and candidate == needle:
            return node.get("item_raw"), node
        if match_mode == "contains" and needle.lower() in candidate.lower():
            return node.get("item_raw"), node
    return None, None


def find_item_by_property(
    container_raw,
    property_name: str,
    value: str,
    start_after_raw: Optional[object] = None,
) -> dict[str, Any]:
    """Find a child item via ItemContainerPattern or subtree walk fallback."""
    prop_key = _norm_property_name(property_name)
    prop_id = _UIA_PROPERTY_IDS.get(prop_key)
    needle = (value or "").strip()
    if not needle:
        return {"success": False, "error": "value is required"}

    if _has_pattern(container_raw, "ItemContainer"):
        try:
            pat = _iface(container_raw, "ItemContainer")
            start_iface = None
            if start_after_raw is not None:
                start_iface = _element_iface(start_after_raw)
            if prop_id is None:
                raise ValueError(f"Unsupported property for ItemContainer: {property_name}")
            found = pat.FindItemByProperty(start_iface, prop_id, needle)
            wrapper = _wrap_com_element(found)
            if wrapper is None:
                return {"success": False, "error": f"Item not found for {property_name}={value!r}"}
            payload = _element_dict(wrapper)
            return {
                "success": True,
                "method": "ItemContainer.FindItemByProperty",
                "property": property_name,
                "value": needle,
                **payload,
            }
        except Exception:
            pass

    item_raw, item = _fallback_find_item(
        container_raw,
        property_name=property_name,
        value=needle,
        start_after_raw=start_after_raw,
    )
    if not item_raw:
        return {
            "success": False,
            "error": f"Item not found for {property_name}={value!r}",
        }
    return {
        "success": True,
        "method": "subtree_walk",
        "property": property_name,
        "value": needle,
        "name": item.get("name", ""),
        "automation_id": item.get("automation_id", ""),
        "role": item.get("role", ""),
        "x": item.get("x", 0),
        "y": item.get("y", 0),
        "width": item.get("width", 0),
        "height": item.get("height", 0),
    }


def apply_pattern_action(raw, pattern_name: str, action: str, **kwargs) -> dict[str, Any]:
    """Apply a named UIA pattern action on a raw pywinauto wrapper."""
    action_norm = (action or "").strip().lower()
    if not _has_pattern(raw, pattern_name):
        return {"success": False, "error": f"{pattern_name} pattern not supported"}

    try:
        pat = _iface(raw, pattern_name)
        if pattern_name == "Invoke":
            pat.Invoke()
            return {"success": True, "method": "InvokePattern.Invoke", "pattern": pattern_name}
        if pattern_name == "Toggle":
            current = getattr(pat, "CurrentToggleState", 0)
            want_on = action_norm in ("on", "true", "1", "toggle_on", "check")
            want_off = action_norm in ("off", "false", "0", "toggle_off", "uncheck")
            if want_on and current == 1:
                return {"success": True, "method": "TogglePattern (already on)", "pattern": pattern_name}
            if want_off and current == 0:
                return {"success": True, "method": "TogglePattern (already off)", "pattern": pattern_name}
            pat.Toggle()
            return {"success": True, "method": "TogglePattern.Toggle", "pattern": pattern_name}
        if pattern_name == "SelectionItem":
            pat.Select()
            return {"success": True, "method": "SelectionItemPattern.Select", "pattern": pattern_name}
        if pattern_name == "ExpandCollapse":
            if action_norm in ("collapse", "closed"):
                pat.Collapse()
                return {"success": True, "method": "ExpandCollapse.Collapse", "pattern": pattern_name}
            pat.Expand()
            return {"success": True, "method": "ExpandCollapse.Expand", "pattern": pattern_name}
        if pattern_name == "ScrollItem":
            pat.ScrollIntoView()
            return {"success": True, "method": "ScrollItem.ScrollIntoView", "pattern": pattern_name}
        if pattern_name == "VirtualizedItem":
            pat.Realize()
            return {"success": True, "method": "VirtualizedItem.Realize", "pattern": pattern_name}
        if pattern_name == "Value" and action_norm in ("set", "setvalue"):
            pat.SetValue(str(kwargs.get("value", "")))
            return {"success": True, "method": "ValuePattern.SetValue", "pattern": pattern_name}
        return {"success": False, "error": f"Unsupported action {action!r} for {pattern_name}"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}

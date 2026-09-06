"""Activate a UIA element via patterns, then optional coordinate fallback."""
from __future__ import annotations

from typing import Any, Optional


def _raw_element(raw: Any) -> Any:
    if hasattr(raw, "element_info") and getattr(raw.element_info, "element", None) is not None:
        return raw.element_info.element
    return raw


def activate_element(
    raw: Any,
    *,
    mode: str = "auto",
    strict_patterns: bool = False,
    automation_id: Optional[str] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Try UIA patterns (Invoke, SelectionItem, Toggle), then UIA click fallback."""
    from detection.uia_patterns import apply_pattern_action

    element = _raw_element(raw)
    pattern_chain = (
        ("Invoke", "invoke"),
        ("SelectionItem", "select"),
        ("Toggle", "toggle"),
        ("ExpandCollapse", "expand"),
    )
    if mode in ("auto", "pattern", "invoke"):
        for pattern_name, action in pattern_chain:
            out = apply_pattern_action(element, pattern_name, action, **kwargs)
            if out.get("success"):
                return out

    if strict_patterns:
        return {"success": False, "error": "strict_patterns blocked coordinate fallback"}

    from detection.backends.uia_backend import _get_clickable_point, _pywinauto_to_element
    from tools.input_tools import do_click

    x, y = _get_clickable_point(element)
    if x is None or y is None:
        converted = _pywinauto_to_element(element)
        if converted is not None:
            x, y = _get_clickable_point(converted)
    if x is not None and y is not None:
        do_click(int(x), int(y))
        return {"success": True, "method": "uia_click"}
    return {"success": False, "error": "no activation path"}

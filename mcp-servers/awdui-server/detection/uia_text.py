"""Read visible text from UIA nodes (LegacyIAccessible / name / editable cascade)."""
from __future__ import annotations

import re
from typing import Any, Optional

_PLACEHOLDER_HINTS = (
    "escribe un mensaje",
    "type a message",
    "write a message",
    "placeholder",
    "enter text",
)


def get_item_text(raw) -> str:
    try:
        from pywinauto.uia_defines import get_elem_interface

        leg = get_elem_interface(raw.element_info.element, "LegacyIAccessible")
        val = getattr(leg, "CurrentName", None) or getattr(leg, "CurrentValue", None)
        if val:
            return str(val).strip()
    except Exception:
        pass
    try:
        return (raw.element_info.name or "").strip()
    except Exception:
        return ""


def get_cell_text(raw) -> str:
    return get_item_text(raw)


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def is_placeholder_text(text: str) -> bool:
    low = _norm(text).lower()
    if not low:
        return True
    return any(hint in low for hint in _PLACEHOLDER_HINTS)


def _prop_chain(properties: dict) -> list[tuple[str, str]]:
    patterns = properties.get("patterns") or {}
    if isinstance(patterns, dict) and "Value" in patterns:
        val = patterns.get("Value") or {}
        if isinstance(val, dict):
            current = _norm(val.get("value") or val.get("Value") or "")
            if current:
                yield "ValuePattern", current
    for key in ("value", "Value", "text", "name"):
        current = _norm(properties.get(key))
        if current:
            yield key, current
    leg = properties.get("LegacyIAccessible") or properties.get("legacy")
    if isinstance(leg, dict):
        for key in ("value", "name"):
            current = _norm(leg.get(key))
            if current:
                yield f"LegacyIAccessible.{key}", current


def read_editable_text(
    properties: dict,
    *,
    automation_id: Optional[str] = None,
    name: Optional[str] = None,
    window_title: Optional[str] = None,
    allow_clipboard: bool = True,
) -> dict[str, Any]:
    """Cascade read for contenteditable / Edit controls when Value is stale."""
    tried: list[str] = []
    for method, text in _prop_chain(properties):
        tried.append(method)
        if text and not is_placeholder_text(text):
            return {"success": True, "text": text, "read_method": method, "tried": tried}

    if allow_clipboard and (automation_id or name):
        clip = _read_via_clipboard(
            automation_id=automation_id,
            name=name,
            window_title=window_title,
        )
        if clip.get("success"):
            clip["tried"] = tried + ["clipboard"]
            return clip
        tried.append("clipboard")

    last = ""
    for _, text in _prop_chain(properties):
        last = text
    return {
        "success": bool(last) and not is_placeholder_text(last),
        "text": last,
        "read_method": tried[-1] if tried else "none",
        "tried": tried,
        "placeholder": is_placeholder_text(last),
    }


def _read_via_clipboard(
    *,
    automation_id: Optional[str] = None,
    name: Optional[str] = None,
    window_title: Optional[str] = None,
) -> dict[str, Any]:
    try:
        from tools.ui_automation import do_click_element
        from tools.input_tools import do_send_keys
        from tools.manage import do_clipboard_read

        click = do_click_element(
            automation_id=automation_id,
            name=name,
            window_title=window_title,
            remember=False,
        )
        if not click.get("success"):
            return {"success": False, "error": click.get("error", "focus failed")}
        do_send_keys("ctrl+a")
        text = _norm(do_clipboard_read())
        if text and not is_placeholder_text(text):
            return {"success": True, "text": text, "read_method": "clipboard"}
        return {"success": False, "text": text, "read_method": "clipboard", "placeholder": True}
    except Exception as exc:
        return {"success": False, "error": str(exc)}

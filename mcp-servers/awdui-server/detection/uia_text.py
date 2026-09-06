"""Read visible text from UIA nodes (LegacyIAccessible / name)."""
from __future__ import annotations


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

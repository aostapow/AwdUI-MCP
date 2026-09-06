"""WinForms ComboBox enumeration (UIA + Win32 CB_* fallback)."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Any, Optional

from detection.uia_text import get_item_text
from detection.uia_tree import _walk_control_tree, element_fields


def _wrap_raw(raw):
    from detection.uia_tree import _wrap_raw as _default_wrap

    return _default_wrap(raw)

CB_GETCOUNT = 0x0146
CB_GETLBTEXT = 0x0148
CB_GETLBTEXTLEN = 0x0149
CB_GETITEMRECT = 0x014A


def _is_plausible_item(name: str, filter_text: str) -> bool:
    text = (name or "").strip()
    if not text:
        return False
    if text.endswith(":"):
        return False
    if len(text) < 2:
        return False
    if filter_text and filter_text.lower() not in text.lower():
        return False
    return True


def is_placeholder_item(item: dict) -> bool:
    return (
        int(item.get("x", 0)) == 0
        and int(item.get("y", 0)) == 0
        and int(item.get("width", 0)) <= 1
        and int(item.get("height", 0)) <= 1
        and bool(item.get("win32_hwnd"))
    )


def item_requires_click_operation(item: dict) -> bool:
    return (item.get("selection_via") or "") == "click"


def click_target_for_item(item: dict) -> dict[str, int]:
    x = int(item.get("x", 0)) + int(item.get("width", 0)) // 2
    y = int(item.get("y", 0)) + int(item.get("height", 0)) // 2
    return {"x": x, "y": y}


def combolbox_item_screen_rect(hwnd: int, index: int) -> tuple[int, int, int, int]:
    """Map ComboLBox item index to screen rect via CB_GETITEMRECT."""
    user32 = ctypes.windll.user32

    class _RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    rect = _RECT()
    user32.SendMessageW(hwnd, CB_GETITEMRECT, index, ctypes.byref(rect))
    pt_tl = wintypes.POINT(rect.left, rect.top)
    pt_br = wintypes.POINT(rect.right, rect.bottom)
    user32.ClientToScreen(hwnd, ctypes.byref(pt_tl))
    user32.ClientToScreen(hwnd, ctypes.byref(pt_br))
    return pt_tl.x, pt_tl.y, pt_br.x - pt_tl.x, pt_br.y - pt_tl.y


def _enumerate_uia_items(root, filter_text: str = "") -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for raw in _walk_control_tree(root):
        fields = element_fields(_wrap_raw(raw))
        if not fields:
            continue
        role = (fields.get("role") or "").strip()
        if role not in ("ListItem", "ComboBox", "List"):
            continue
        text = get_item_text(raw)
        name = (text or fields.get("name") or "").strip()
        if not _is_plausible_item(name, filter_text):
            continue
        items.append(
            {
                "name": name,
                "role": role if role == "ListItem" else "ListItem",
                "x": int(fields["x"]),
                "y": int(fields["y"]),
                "width": int(fields["width"]),
                "height": int(fields["height"]),
                "automation_id": fields.get("automation_id", "") or "",
                "item_raw": raw,
            }
        )
    return items


def _native_handle(raw) -> int:
    try:
        return int(raw.element_info.handle or 0)
    except Exception:
        return 0


def _combo_popup_roots(raw, combo_wrapper=None) -> list:
    return []


def _win32_list_items(hwnd: int, filter_text: str = "") -> list[dict[str, Any]]:
    if not hwnd:
        return []
    user32 = ctypes.windll.user32
    count = int(user32.SendMessageW(hwnd, CB_GETCOUNT, 0, 0))
    items: list[dict[str, Any]] = []
    for idx in range(count):
        length = int(user32.SendMessageW(hwnd, CB_GETLBTEXTLEN, idx, 0))
        if length <= 0:
            continue
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.SendMessageW(hwnd, CB_GETLBTEXT, idx, buf)
        name = buf.value.strip()
        if not _is_plausible_item(name, filter_text):
            continue
        try:
            sx, sy, sw, sh = combolbox_item_screen_rect(hwnd, idx)
        except Exception:
            sx, sy, sw, sh = 0, 0, 1, 1
        placeholder = sw <= 1 and sh <= 1
        item = {
            "name": name,
            "role": "ListItem",
            "x": sx,
            "y": sy,
            "width": sw,
            "height": sh,
            "automation_id": "",
            "item_raw": None,
            "win32_index": idx,
            "win32_hwnd": hwnd,
        }
        if not placeholder and sw > 10 and sh > 10:
            item["selection_via"] = "click"
        items.append(item)
    return items


def apply_filter_to_combo(*_a, **_k) -> None:
    return None


def expand_combo(*_a, **_k) -> None:
    return None


def _collect_with_raw(root, filter_text: str = "") -> list[dict[str, Any]]:
    return _enumerate_uia_items(root, filter_text=filter_text)


def collect_combo_items(
    root,
    filter_text: str = "",
    offset: int = 0,
    limit: int = 50,
    combo_wrapper=None,
) -> dict[str, Any]:
    limit = max(1, min(int(limit or 50), 200))
    offset = max(0, int(offset or 0))
    expand_combo(root, combo_wrapper=combo_wrapper)
    apply_filter_to_combo(root, filter_text=filter_text, combo_wrapper=combo_wrapper)
    items = _enumerate_uia_items(root, filter_text=filter_text)
    source = "uia"
    if not items:
        hwnd = _native_handle(root)
        for popup in _combo_popup_roots(root, combo_wrapper):
            hwnd = _native_handle(popup) or hwnd
        win32_items = _win32_list_items(hwnd, filter_text=filter_text)
        if win32_items:
            items = win32_items
            source = "winforms_combo"
    matched_total = len(items)
    page = items[offset : offset + limit]
    return {
        "items": page,
        "returned": len(page),
        "matched_total": matched_total,
        "has_more": offset + len(page) < matched_total,
        "offset": offset,
        "limit": limit,
        "source": source,
    }


def find_combo_item(root, value: str, combo_wrapper=None) -> Optional[tuple[Optional[object], dict]]:
    needle = (value or "").strip().lower()
    if not needle:
        return None
    for item in _collect_with_raw(root, filter_text=value):
        blob = (item.get("name") or "").lower()
        if needle in blob:
            return item.get("item_raw"), item
    batch = collect_combo_items(root, filter_text=value, combo_wrapper=combo_wrapper, limit=200)
    for item in batch.get("items") or []:
        blob = (item.get("name") or "").lower()
        if needle in blob:
            return item.get("item_raw"), item
    return None

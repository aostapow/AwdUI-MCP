"""Paginated ListItem / DataItem collection under a control subtree."""
from __future__ import annotations

import re
from typing import Any, Optional

from detection.uia_text import get_item_text
from detection.uia_tree import _walk_control_tree, _wrap_raw

_ITEM_ROLES = frozenset({"ListItem", "DataItem", "TreeItem", "MenuItem"})


def _matches_filter(item: dict, filter_text: str) -> bool:
    if not filter_text:
        return True
    needle = filter_text.lower()
    blob = " ".join(
        [
            (item.get("name") or ""),
            (item.get("value") or ""),
            (item.get("display_text") or ""),
        ]
    ).lower()
    return needle in blob


def _list_item_nodes(root) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for raw in _walk_control_tree(root):
        det = _wrap_raw(raw)
        if not det:
            continue
        role = (det.role or "").strip()
        if role not in _ITEM_ROLES:
            continue
        text = get_item_text(raw)
        name = (det.name or text or "").strip()
        item = {
            "name": name,
            "role": role,
            "x": int(det.x),
            "y": int(det.y),
            "width": int(det.width),
            "height": int(det.height),
            "automation_id": getattr(det, "automation_id", "") or "",
            "value": text or getattr(det, "value", "") or "",
            "display_text": text,
            "item_raw": raw,
        }
        items.append(item)
    return items


def collect_control_items(
    root,
    filter_text: str = "",
    offset: int = 0,
    limit: int = 50,
) -> dict[str, Any]:
    """Return a page of item dicts under *root*."""
    limit = max(1, min(int(limit or 50), 200))
    offset = max(0, int(offset or 0))
    nodes = _list_item_nodes(root)
    filtered = [n for n in nodes if _matches_filter(n, filter_text)]
    matched_total = len(filtered)
    page = filtered[offset : offset + limit]
    return {
        "items": page,
        "returned": len(page),
        "matched_total": matched_total,
        "has_more": offset + len(page) < matched_total,
        "offset": offset,
        "limit": limit,
    }


def find_item_raw_by_name(root, value: str) -> tuple[Optional[object], Optional[dict]]:
    needle = (value or "").strip().lower()
    if not needle:
        return None, None
    best: Optional[dict] = None
    best_raw = None
    for item in _list_item_nodes(root):
        blob = " ".join(
            [(item.get("name") or ""), (item.get("value") or ""), (item.get("display_text") or "")]
        ).lower()
        if needle in blob:
            best = item
            best_raw = item.get("item_raw")
            break
    if best is None:
        return None, None
    return best_raw, best


_ROW_CELL_RE = re.compile(r"^(.+?)\s+row\s+(\d+)$", re.IGNORECASE)


def parse_row_cell_name(name: str) -> Optional[tuple[str, int]]:
    m = _ROW_CELL_RE.match((name or "").strip())
    if not m:
        return None
    return m.group(1).strip().lower(), int(m.group(2))

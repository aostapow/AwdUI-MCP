"""Direct grid cell access by row/column (UIA GridPattern + DevExpress fallback)."""
from __future__ import annotations

from typing import Any, Optional

from detection.grid_rows import group_grid_rows


def _grid_column_names(rows: list[dict[str, Any]]) -> list[str]:
    cols: set[str] = set()
    for row in rows:
        cols.update((row.get("cells") or {}).keys())
    return sorted(cols)


def _pick_row(rows: list[dict[str, Any]], row_index: int) -> Optional[dict[str, Any]]:
    for row in rows:
        if int(row.get("row_index", -1)) == int(row_index):
            return row
    ordered = sorted(rows, key=lambda r: int(r.get("row_index", 0)))
    if 0 <= int(row_index) < len(ordered):
        return ordered[int(row_index)]
    return None


def _resolve_column_key(
    rows: list[dict[str, Any]],
    column_index: int,
    column_name: str,
) -> tuple[str, int]:
    col_names = _grid_column_names(rows)
    explicit = (column_name or "").strip().lower()
    if explicit:
        return explicit, column_index
    if col_names and 0 <= int(column_index) < len(col_names):
        return col_names[int(column_index)], int(column_index)
    if col_names:
        return col_names[0], 0
    return "", int(column_index)


def get_grid_item_devexpress(
    root,
    row_index: int,
    column_index: int = 0,
    column_name: str = "",
) -> Optional[dict[str, Any]]:
    rows = group_grid_rows(root)
    if not rows:
        return None
    picked = _pick_row(rows, row_index)
    if not picked:
        return None
    col_key, col_idx = _resolve_column_key(rows, column_index, column_name)
    cells = picked.get("cells") or {}
    cell_raws = picked.get("cell_raws") or {}
    if col_key and col_key in cells:
        value = cells[col_key]
        raw = cell_raws.get(col_key)
    elif cells:
        col_key = next(iter(cells))
        value = cells[col_key]
        raw = cell_raws.get(col_key)
    else:
        value = picked.get("name", "")
        raw = next(iter(cell_raws.values()), None)
    return {
        "row_index": picked.get("row_index", row_index),
        "column_index": col_idx,
        "column_name": col_key,
        "value": value,
        "name": value or picked.get("name", ""),
        "cells": cells,
        "x": int(picked.get("x", 0)),
        "y": int(picked.get("y", 0)),
        "width": int(picked.get("width", 0)),
        "height": int(picked.get("height", 0)),
        "source": "grid_rows",
        "item_raw": raw,
    }


def get_grid_item_pattern(raw, row_index: int, column_index: int) -> Optional[dict[str, Any]]:
    """Read cell via UIA GridPattern.GetItem when available."""
    try:
        from pywinauto.uia_defines import get_elem_interface
        from detection.backends.uia_backend import _pywinauto_to_element
        from detection.uia_text import get_cell_text

        element = raw.element_info.element
        for pattern_name in ("Grid", "Table"):
            try:
                pattern = get_elem_interface(element, pattern_name)
                cell_raw = pattern.GetItem(int(row_index), int(column_index))
            except Exception:
                continue
            if cell_raw is None:
                continue
            try:
                from pywinauto.controls.uiawrapper import UIAWrapper

                wrapper = UIAWrapper(cell_raw) if not hasattr(cell_raw, "element_info") else cell_raw
            except Exception:
                wrapper = cell_raw
            det = _pywinauto_to_element(wrapper)
            if not det:
                continue
            value = get_cell_text(wrapper) or det.name or getattr(det, "value", "") or ""
            return {
                "row_index": int(row_index),
                "column_index": int(column_index),
                "column_name": (det.name or "").strip(),
                "value": value,
                "name": value or det.name or "",
                "x": int(det.x),
                "y": int(det.y),
                "width": int(det.width),
                "height": int(det.height),
                "automation_id": det.automation_id or "",
                "role": det.role or "",
                "source": f"uia_{pattern_name.lower()}",
                "item_raw": wrapper,
            }
    except Exception:
        return None
    return None


def get_grid_item(
    root,
    row_index: int,
    column_index: int = 0,
    column_name: str = "",
) -> Optional[dict[str, Any]]:
    """Return grid cell metadata; tries UIA pattern then DevExpress row assembly."""
    pattern_hit = get_grid_item_pattern(root, row_index, column_index)
    if pattern_hit:
        return pattern_hit
    return get_grid_item_devexpress(
        root,
        row_index=row_index,
        column_index=column_index,
        column_name=column_name,
    )


def public_grid_item(item: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if not item:
        return None
    out = {k: v for k, v in item.items() if k not in ("item_raw", "row")}
    return out

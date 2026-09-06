"""DevExpress-style grid row assembly from DataItem cells."""
from __future__ import annotations

from typing import Any, Optional

from detection.uia_find import parse_row_cell_name
from detection.uia_text import get_cell_text
from detection.uia_tree import _walk_control_tree, element_fields


def _wrap_raw(raw):
    from detection.uia_tree import _wrap_raw as _default_wrap

    return _default_wrap(raw)


def group_grid_rows(root) -> list[dict[str, Any]]:
    cells_by_row: dict[int, dict[str, Any]] = {}
    for raw in _walk_control_tree(root):
        fields = element_fields(_wrap_raw(raw))
        if not fields or (fields.get("role") or "") != "DataItem":
            continue
        parsed = parse_row_cell_name(fields.get("name") or "")
        if not parsed:
            continue
        col, row_idx = parsed
        text = get_cell_text(raw)
        row = cells_by_row.setdefault(
            row_idx,
            {
                "row_index": row_idx,
                "name": "",
                "cells": {},
                "cell_raws": {},
                "x": int(fields["x"]),
                "y": int(fields["y"]),
                "width": int(fields["width"]),
                "height": int(fields["height"]),
            },
        )
        row["cells"][col] = text
        row["cell_raws"][col] = raw
        if not row["name"] and text:
            row["name"] = text
        row["x"] = min(row["x"], int(fields["x"]))
        row["y"] = min(row["y"], int(fields["y"]))
    return [cells_by_row[k] for k in sorted(cells_by_row)]


def row_matches(row: dict, filter_text: str) -> bool:
    needle = (filter_text or "").strip().lower()
    if not needle:
        return True
    blob = " ".join([row.get("name", "")] + list((row.get("cells") or {}).values())).lower()
    return needle in blob


def collect_grid_rows(
    root,
    filter_text: str = "",
    offset: int = 0,
    limit: int = 50,
) -> dict[str, Any]:
    limit = max(1, min(int(limit or 50), 200))
    offset = max(0, int(offset or 0))
    rows = group_grid_rows(root)
    filtered = [r for r in rows if row_matches(r, filter_text)]
    matched_total = len(filtered)
    page = filtered[offset : offset + limit]
    items = []
    for row in page:
        items.append(
            {
                "name": row.get("name", ""),
                "row_index": row.get("row_index"),
                "cells": row.get("cells", {}),
                "x": row.get("x", 0),
                "y": row.get("y", 0),
                "width": row.get("width", 0),
                "height": row.get("height", 0),
                "item_raw": row.get("cell_raws", {}).get(next(iter(row.get("cells", {})), ""), None),
                "row": row,
            }
        )
    return {
        "items": items,
        "returned": len(items),
        "matched_total": matched_total,
        "has_more": offset + len(items) < matched_total,
        "offset": offset,
        "limit": limit,
    }


def find_grid_row(
    root,
    value: str,
    column: str = "",
) -> Optional[tuple[Optional[object], dict]]:
    col = (column or "").strip().lower()
    needle = (value or "").strip().lower()
    for row in group_grid_rows(root):
        if not row_matches(row, needle):
            continue
        if col:
            cell_val = (row.get("cells") or {}).get(col, "")
            if needle not in (cell_val or "").lower():
                continue
            raw = (row.get("cell_raws") or {}).get(col)
        else:
            raw = next(iter((row.get("cell_raws") or {}).values()), None)
        item = {
            "name": row.get("name", ""),
            "row_index": row.get("row_index"),
            "cells": row.get("cells", {}),
            "x": row.get("x", 0),
            "y": row.get("y", 0),
            "width": row.get("width", 0),
            "height": row.get("height", 0),
            "item_raw": raw,
            "row": row,
        }
        return raw, item
    return None


def select_grid_row_by_index(root, row_index: int, column: str = "") -> Optional[tuple[Optional[object], dict]]:
    col = (column or "").strip().lower()
    for row in group_grid_rows(root):
        if int(row.get("row_index", -1)) != int(row_index):
            continue
        if col:
            raw = (row.get("cell_raws") or {}).get(col)
            name = (row.get("cells") or {}).get(col, row.get("name", ""))
        else:
            raw = next(iter((row.get("cell_raws") or {}).values()), None)
            name = row.get("name", "")
        return raw, {
            "name": name,
            "row_index": row.get("row_index"),
            "cells": row.get("cells", {}),
            "item_raw": raw,
            "row": row,
        }
    return None

"""Parse FarPoint / COBISSpread cells from UIA subtree."""
from __future__ import annotations

import re
from typing import Any, Optional

from detection.uia_text import get_cell_text
from detection.uia_tree import _walk_control_tree, _wrap_raw

_FARPOINT_RE = re.compile(
    r"row\s*(\d+)\s*,?\s*column\s*(\d+)",
    re.IGNORECASE,
)
_DEVEXPRESS_RE = re.compile(r"^(.+?)\s+row\s+(\d+)$", re.IGNORECASE)


def _parse_cell(name: str, description: str = "") -> Optional[tuple[int, int, str]]:
    blob = f"{name} {description}".strip()
    m = _FARPOINT_RE.search(blob)
    if m:
        return int(m.group(1)), int(m.group(2)), blob
    m2 = _DEVEXPRESS_RE.match((name or "").strip())
    if m2:
        return int(m2.group(2)), 0, blob
    return None


def collect_farpoint_cells(raw, index_base: int = 1) -> dict[str, Any]:
    """Build headers + rows from FarPoint-style UIA cell names."""
    cells: dict[tuple[int, int], str] = {}
    max_row = 0
    max_col = 0

    for child in _walk_control_tree(raw):
        det = _wrap_raw(child)
        if not det:
            continue
        name = (det.name or "").strip()
        desc = getattr(det, "accessible_description", "") or ""
        parsed = _parse_cell(name, desc)
        if not parsed:
            continue
        row_i, col_i, _ = parsed
        text = (get_cell_text(child) or det.name or getattr(det, "value", "") or "").strip()
        if row_i == 0 and col_i == 0 and not text:
            continue
        cells[(row_i, col_i)] = text
        max_row = max(max_row, row_i)
        max_col = max(max_col, col_i)

    if not cells:
        return {}

    header_row = index_base - 1 if index_base == 1 else 0
    headers: list[str] = []
    for col in range(max_col + 1):
        headers.append(cells.get((header_row, col), f"col_{col}"))

    data_rows: list[list[str]] = []
    start_row = index_base if index_base == 1 else 1
    for row in range(start_row, max_row + 1):
        if row == header_row and index_base == 1:
            continue
        row_vals = [cells.get((row, col), "") for col in range(max_col + 1)]
        if any(v.strip() for v in row_vals):
            data_rows.append(row_vals)

    return {
        "headers": headers,
        "rows": data_rows,
        "row_count": len(data_rows),
        "total_rows": len(data_rows),
        "offset": 0,
        "limit": len(data_rows),
        "has_more": False,
        "source": "cen_farpoint_uia",
        "index_base": index_base,
    }

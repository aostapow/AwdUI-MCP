"""Select a row in a COBIS grid by clicking the row band."""
from __future__ import annotations

from typing import Any, Optional

from grid.read import read_cobis_grid
from grid.resolve import resolve_grid


def select_cobis_grid_row(
    automation_id: str = "",
    name: str = "",
    row: int = 1,
    column: int = 1,
    window_title: Optional[str] = None,
    double_click: bool = False,
) -> dict[str, Any]:
    if row < 1:
        return {"success": False, "error": "row must be >= 1 (1-based CEN convention)"}

    raw, element, scope = resolve_grid(automation_id, name, window_title)
    if not raw:
        return {"success": False, **scope}

    table = read_cobis_grid(
        automation_id=automation_id,
        name=name,
        window_title=window_title,
        limit=500,
    )
    if not table.get("success"):
        return table

    index_base = int(table.get("index_base") or 1)
    data_row = int(row) - index_base
    data_col = max(0, int(column) - index_base)
    rows = table.get("rows") or []
    if data_row < 0 or data_row >= len(rows):
        return {"success": False, "error": f"row {row} not in readable grid"}

    gx = int(element.get("x") or 0)
    gy = int(element.get("y") or 0)
    gh = int(element.get("height") or 0)
    row_count = max(len(rows), 1)
    row_height = max(gh // (row_count + 1), 12)
    header_offset = row_height
    click_y = gy + header_offset + data_row * row_height + row_height // 2
    col_count = max(len(rows[data_row]), 1)
    gw = int(element.get("width") or 0)
    col_width = max(gw // col_count, 20)
    click_x = gx + data_col * col_width + col_width // 2

    from tools.input_tools import do_click

    button = "left"
    if double_click:
        do_click(click_x, click_y, button=button)
        do_click(click_x, click_y, button=button)
    else:
        do_click(click_x, click_y, button=button)

    return {
        "success": True,
        "row": row,
        "column": column,
        "click": {"x": click_x, "y": click_y},
        "method": "row_band_click",
        "double_click": double_click,
        "resolved_window_title": scope.get("resolved_title") or "",
        "note": "Approximate row click from grid bbox; verify selection in UI",
    }

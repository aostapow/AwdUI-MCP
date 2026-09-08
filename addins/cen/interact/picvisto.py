"""picVisto grid row toggle (FTRAN024 maintenance pattern)."""
from __future__ import annotations

from typing import Any, Optional

from grid.select import select_cobis_grid_row


def toggle_row_visto(
    automation_id: str = "",
    name: str = "",
    row: int = 1,
    visto_column: int = 1,
    window_title: Optional[str] = None,
) -> dict[str, Any]:
    """Double-click picVisto column to toggle row selection in maintenance grids."""
    if row < 1:
        return {"success": False, "error": "row must be >= 1"}

    result = select_cobis_grid_row(
        automation_id=automation_id,
        name=name,
        row=row,
        column=visto_column,
        window_title=window_title,
        double_click=True,
    )
    return {
        **result,
        "action": "toggle_row_visto",
        "visto_column": visto_column,
        "pattern": "FTRAN024 picVisto double-click",
    }

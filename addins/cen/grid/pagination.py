"""Grid pagination heuristics from CEN code (grd.Tag, MaximoRows=19)."""
from __future__ import annotations

import json
from typing import Any, Optional

MAXIMO_ROWS = 19
PAGINATION_THRESHOLD = 20


def grid_pagination_status(
    automation_id: str = "",
    name: str = "",
    window_title: Optional[str] = None,
    toolbar_window_title: Optional[str] = None,
) -> dict[str, Any]:
    """Infer if Siguiente/Buscar pagination likely applies after last read."""
    from grid.read import read_cobis_grid
    from toolbar import list_cobis_toolbar

    table = read_cobis_grid(
        automation_id=automation_id,
        name=name,
        window_title=window_title,
        limit=500,
    )
    toolbar = list_cobis_toolbar(toolbar_window_title or window_title)

    row_count = int(table.get("total_rows") or table.get("row_count") or 0)
    siguiente = None
    buscar = None
    for btn in toolbar.get("buttons") or []:
        cap = (btn.get("name") or "").lower().replace("&", "")
        if "sigu" in cap or "sigte" in cap:
            siguiente = btn
        if "buscar" in cap:
            buscar = btn

    likely_more = row_count >= PAGINATION_THRESHOLD
    siguiente_enabled = bool(siguiente and siguiente.get("enabled", True))

    return {
        "success": table.get("success", False),
        "grid": automation_id or name,
        "visible_rows": row_count,
        "maximo_rows": MAXIMO_ROWS,
        "likely_more_pages": likely_more,
        "siguiente_button": siguiente,
        "siguiente_enabled": siguiente_enabled,
        "recommendation": (
            "cen_click_toolbar(caption='Siguiente') or 'Sigtes'"
            if likely_more and siguiente_enabled
            else "no pagination needed or Siguiente disabled"
        ),
        "grid_read": {
            "source": table.get("source"),
            "grid_type": table.get("grid_type"),
        },
    }

"""COBISSpread context menu (FGrdOpcionesClass)."""
from __future__ import annotations

from typing import Any, Optional

from detect.modals import detect_modal
from grid.resolve import resolve_grid


def open_grid_context_menu(
    automation_id: str = "",
    name: str = "",
    window_title: Optional[str] = None,
    row: int = 1,
    column: int = 1,
) -> dict[str, Any]:
    """Right-click grid cell to open FGrdOpciones / spread context menu."""
    raw, element, scope = resolve_grid(automation_id, name, window_title)
    if not raw:
        return {"success": False, **scope}

    from grid.select import select_cobis_grid_row

    anchor = select_cobis_grid_row(
        automation_id=automation_id,
        name=name,
        row=row,
        column=column,
        window_title=window_title,
        double_click=False,
    )
    if not anchor.get("success"):
        return anchor

    click = anchor.get("click") or {}
    x = int(click.get("x") or 0)
    y = int(click.get("y") or 0)

    from tools.input_tools import do_click

    do_click(x, y, button="right")

    modal = detect_modal(window_title)
    return {
        "success": True,
        "action": "open_grid_context",
        "click": click,
        "modal": modal,
        "resolved_window_title": scope.get("resolved_title") or "",
        "hint": "Use cen_grid_context_action if FGrdOpciones opens",
    }


def grid_context_action(
    action: str = "",
    window_title: Optional[str] = None,
) -> dict[str, Any]:
    """Click action in grid options popup (Ordenar, Exportar, etc.)."""
    if not action:
        return {"success": False, "error": "action caption required"}

    from tools.ui_automation import do_click_element, do_find_element

    found = do_find_element(
        name=action,
        window_title=window_title or "",
        fuzzy_match=True,
        include_offscreen=True,
    )
    if isinstance(found, str):
        import json

        found = json.loads(found)

    if not found.get("found"):
        return {
            "success": False,
            "error": f"action '{action}' not found",
            "modal": detect_modal(window_title),
        }

    el = found["elements"][0]
    click = do_click_element(
        automation_id=el.get("automation_id") or None,
        name=el.get("name") or None,
        window_title=window_title or "",
    )
    ok = isinstance(click, dict) and click.get("success", True)
    return {
        "success": bool(ok),
        "action": action,
        "click_result": click,
        "modal": detect_modal(window_title),
    }

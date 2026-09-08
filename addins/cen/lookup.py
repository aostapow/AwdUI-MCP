"""F5 lookup modal (grid_valoresClass) helpers."""
from __future__ import annotations

import json
from typing import Any, Optional


def detect_lookup_modal(window_title: Optional[str] = None) -> dict[str, Any]:
    """Backward-compatible wrapper; prefer detect_modal for full modal typing."""
    from detect.modals import detect_modal

    modal = detect_modal(window_title)
    lookup_types = {"grid_valores", "buscar_cliente", "buscar_convenio"}
    open_modal = modal.get("modal_open") and modal.get("modal_type") in lookup_types
    return {
        **modal,
        "success": True,
        "lookup_open": bool(is_lookup),
        "modal_type": modal.get("modal_type"),
        "confidence": modal.get("confidence", 0.0),
        "grid_control": modal.get("grid_control"),
        "resolved_window_title": modal.get("resolved_window_title") or window_title or "",
    }


def search_lookup(
    search_text: str,
    window_title: Optional[str] = None,
) -> dict[str, Any]:
    from tools.ui_automation import do_click_element, do_set_element_value

    modal = detect_lookup_modal(window_title)
    if not modal.get("lookup_open"):
        return {"success": False, "error": "Lookup modal not detected", **modal}

    modal_type = modal.get("modal_type") or "grid_valores"
    search_fields = {
        "grid_valores": ("txt_comodin",),
        "buscar_cliente": ("txtCampo", "txtCliente"),
        "buscar_convenio": ("txtconvenio",),
    }.get(modal_type, ("txt_comodin", "txtCampo"))

    set_ok = False
    for field_id in search_fields:
        set_res = do_set_element_value(
            search_text, automation_id=field_id, window_title=window_title or ""
        )
        if isinstance(set_res, dict) and set_res.get("success"):
            set_ok = True
            break

    buscar_id = "bb_buscar" if modal_type == "grid_valores" else "cmdBuscar"

    click = do_click_element(automation_id=buscar_id, window_title=window_title or "")
    ok = isinstance(click, dict) and click.get("success")
    return {
        "success": bool(ok and set_ok),
        "action": "search_lookup",
        "modal_type": modal_type,
        "search_text": search_text,
        "click_result": click,
    }


def select_lookup_row(
    row: int = 1,
    window_title: Optional[str] = None,
    double_click: bool = True,
) -> dict[str, Any]:
    from grid.select import select_cobis_grid_row

    modal = detect_lookup_modal(window_title)
    grid_name = modal.get("grid_control") or "gr_SQL"
    confirm_id = modal.get("confirm_control") or "bb_escoger"

    picked = select_cobis_grid_row(
        name=grid_name,
        row=row,
        window_title=window_title,
        double_click=double_click,
    )
    if not picked.get("success"):
        return picked

    from tools.ui_automation import do_click_element

    escoger = do_click_element(automation_id=confirm_id, window_title=window_title or "")
    return {
        "success": True,
        "row": row,
        "grid_click": picked,
        "bb_escoger": escoger,
    }

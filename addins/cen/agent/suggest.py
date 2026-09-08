"""Suggest next MCP action based on CEN form/modal state."""
from __future__ import annotations

from typing import Any, Optional

from detect.forms import match_form_profile
from detect.modals import detect_modal


def suggest_next_action(window_title: Optional[str] = None) -> dict[str, Any]:
    from catalog import list_classified_controls

    catalog = list_classified_controls(window_title, max_depth=6)
    if not catalog.get("success"):
        return catalog

    elems = catalog.get("controls") or []
    title = catalog.get("resolved_window_title") or window_title or ""
    modal = detect_modal(title)
    profile = match_form_profile(title, elems)
    ctx = catalog.get("context") or {}

    suggestions: list[dict[str, str]] = []

    if modal.get("modal_open"):
        mt = modal.get("modal_type")
        if mt == "grid_valores":
            suggestions.append({"tool": "cen_read_grid", "args": "name=gr_SQL"})
            suggestions.append({"tool": "cen_select_lookup_row", "args": "row=1"})
        elif mt == "buscar_cliente":
            suggestions.append({"tool": "cen_read_grid", "args": "name=GrdResultados"})
            suggestions.append({"tool": "cen_click_toolbar", "args": "caption=Escoger"})
        elif mt == "cobis_message":
            suggestions.append({"tool": "cen_handle_dialog", "args": "action=ok"})
        else:
            suggestions.append({"tool": "cen_detect_modal", "args": ""})
        return {
            "success": True,
            "state": "modal_open",
            "modal": modal,
            "suggestions": suggestions,
        }

    if profile.get("matched"):
        suggestions.insert(0, {"tool": "cen_analyze_form", "args": ""})
        fid = profile["form_id"]
        if fid == "FTRANSAC":
            suggestions = [
                {"tool": "cen_set_field", "args": "fill filters txtconvenio/txtmoneda/mskFecha"},
                {"tool": "cen_click_toolbar_intent", "args": "intent=search"},
                {"tool": "cen_read_grid", "args": "name=grdRegistros"},
                {"tool": "cen_grid_pagination", "args": "name=grdRegistros"},
            ]
        elif fid in ("FTRAN024", "FUSUAROL"):
            suggestions = [
                {"tool": "cen_set_field", "args": "txtCampo filters"},
                {"tool": "cen_click_toolbar_intent", "args": "intent=search"},
                {"tool": "cen_select_grid_row", "args": "double_click for picVisto if FTRAN024"},
            ]
        elif fid == "FTRAN292":
            suggestions = [
                {"tool": "cen_set_field", "args": "name=mskCuenta"},
                {"tool": "cen_click_toolbar_intent", "args": "intent=search"},
                {"tool": "cen_click_toolbar", "args": "caption=Escoger"},
            ]
        elif fid == "FTRA2514" or profile.get("trees"):
            suggestions = [
                {"tool": "cen_tristate_list_nodes", "args": f"name={profile.get('trees', ['TVTransaccion'])[0]}"},
                {"tool": "cen_tristate_toggle", "args": "text_contains=<permission>"},
                {"tool": "cen_click_toolbar", "args": "caption=Transmitir"},
            ]
        elif profile.get("selection_pattern") or "picVisto" in str(profile.get("notes", "")):
            suggestions = [
                {"tool": "cen_click_toolbar_intent", "args": "intent=search"},
                {"tool": "cen_toggle_row_visto", "args": "row=1"},
            ]
        else:
            suggestions = [
                {"tool": "cen_get_form_profile", "args": f"form_id={fid}"},
                {"tool": "cen_list_form_controls", "args": ""},
                {"tool": "cen_get_flow_hint", "args": "consulta_estandar"},
            ]
    else:
        grids = [
            c
            for c in elems
            if (c.get("cen") or {}).get("cen_type", "").startswith("cobis_")
            and "grid" in (c.get("cen") or {}).get("cen_type", "")
        ]
        txts = [
            c
            for c in elems
            if (c.get("cen") or {}).get("cen_type")
            in ("cobis_valid_text", "cobis_masked_inbox", "cobis_masked_text")
        ]
        if txts and not grids:
            suggestions.append({"tool": "cen_set_field", "args": f"name={txts[0].get('name')}"})
            suggestions.append({"tool": "cen_click_toolbar", "args": "caption=Buscar"})
        elif grids:
            suggestions.append({"tool": "cen_read_grid", "args": f"name={grids[0].get('name')}"})
        else:
            suggestions.append({"tool": "cen_detect_form_context", "args": ""})
            suggestions.append({"tool": "spy_tree", "args": "max_depth=6"})

    f5_fields = profile.get("f5_fields") or []
    for f in f5_fields[:3]:
        suggestions.append({"tool": "cen_trigger_f5", "args": f"name={f}"})

    return {
        "success": True,
        "state": "form_active",
        "window_title": title,
        "form_profile": profile,
        "context": ctx,
        "suggestions": suggestions[:8],
        "warnings": [
            "Never use cmdBoton index from another form",
            "Complete modal sub-flow before parent actions",
            "Use Salir not window X to close forms",
        ],
    }

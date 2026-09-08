"""COBIS CEN addin — full detection and interaction surface from static code analysis."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from addin_sdk.contract import AddinContext, AddinManifest, AwduiAddin


def _json_out(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


class CenAddin(AwduiAddin):
    manifest = AddinManifest(
        id="cen",
        name="COBIS CEN Frontend",
        version="0.6.0",
        entry_module="cen_addin:CenAddin",
        tool_namespace="cen_",
    )

    def on_load(self, ctx: AddinContext) -> None:
        knowledge_dir = ctx.addin_root / "knowledge"
        self._knowledge: dict[str, Any] = {}
        for name in (
            "controls.json", "flows.json", "modules.json", "modals.json",
            "forms_index.json", "messages.json", "messages_catalog.json",
            "popups_registry.json", "forms_catalog_index.json",
        ):
            path = knowledge_dir / name
            if path.is_file():
                try:
                    self._knowledge[name] = json.loads(path.read_text(encoding="utf-8"))
                except Exception as exc:
                    ctx.log(f"could not load {name}: {exc}")
        map_path = ctx.addin_root / "object_map.json"
        self._object_map: dict[str, Any] = {}
        if map_path.is_file():
            try:
                self._object_map = json.loads(map_path.read_text(encoding="utf-8"))
            except Exception:
                ctx.log(f"could not parse {map_path}")

    def match_app(self, identity: dict, ctx: AddinContext) -> float:
        proc = (identity.get("process_name") or "").lower()
        title = (identity.get("window_title") or "").lower()
        patterns = ctx.manifest.match.get("window_title_patterns") or ["cobis", "cen"]
        proc_names = [p.lower() for p in ctx.manifest.match.get("process_names") or []]
        score = 0.0
        if proc_names and any(p in proc for p in proc_names):
            score = 0.85
        if any(p.lower() in title for p in patterns):
            score = max(score, 0.75)
        return score

    def _forms_catalog_meta(self) -> dict[str, Any]:
        path = Path(__file__).resolve().parent / "knowledge" / "forms_catalog.json"
        if not path.is_file():
            return {"loaded": False}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return {
                "loaded": True,
                "total": data.get("total"),
                "extracted_count": data.get("extracted_count"),
                "curated_count": data.get("curated_count"),
            }
        except Exception:
            return {"loaded": False}

    def register_tools(self, mcp: Any, ctx: AddinContext) -> int:
        from agent.suggest import suggest_next_action
        from catalog import find_controls, list_classified_controls
        from detect.forms import match_form_profile
        from detect.modals import detect_modal
        from grid.pagination import grid_pagination_status
        from interact.security import read_toolbar_security
        from interact.status_bar import read_status_hints
        from detect.forms_catalog import get_form_profile, list_forms, search_forms
        from interact.grid_context import grid_context_action, open_grid_context_menu
        from interact.picvisto import toggle_row_visto
        from agent.analyze import analyze_form
        from detect.forms_catalog import catalog_stats, get_popup_hints
        from detect.messages import classify_message, match_dialog_from_ui
        from interact.user_control import drill_user_control, set_moneda
        from interact.wait_validation import wait_field_stable, wait_toolbar_enabled
        from toolbar import click_cobis_toolbar, click_toolbar_intent, list_cobis_toolbar, resolve_toolbar_intent
        from detect.classifier import classify_element
        from detect.form_context import build_form_context
        from flows import get_flow_hint, list_flows
        from grid.read import detect_cobis_grid, read_cobis_grid, read_cobis_grid_cell
        from grid.select import select_cobis_grid_row
        from interact.dialogs import detect_message_box, handle_dialog
        from interact.f5_help import trigger_f5
        from interact.fields import read_field, set_field
        from interact.outline import outline_expand, outline_select
        from interact.tabs_radios import select_radio, select_tab
        from lookup import detect_lookup_modal, search_lookup, select_lookup_row
        from interact.tristate_tree import list_tristate_nodes, toggle_tristate_node

        @mcp.tool()
        def cen_get_addin_info() -> str:
            """COBIS CEN addin: knowledge base version, products, control types, all cen_* tools."""
            return _json_out(
                {
                    "addin": "cen",
                    "version": self.manifest.version,
                    "knowledge_files": list(self._knowledge.keys()),
                    "products": (self._knowledge.get("modules.json") or {}).get("products", []),
                    "control_types": [
                        c["id"] for c in (self._knowledge.get("controls.json") or {}).get("controls", [])
                    ],
                    "flows": list((self._knowledge.get("flows.json") or {}).get("flows", {}).keys()),
                    "forms_catalog": self._forms_catalog_meta(),
                }
            )

        @mcp.tool()
        def cen_classify_control(
            automation_id: str = "",
            name: str = "",
            class_name: str = "",
            role: str = "",
        ) -> str:
            """Classify a control into CEN type (cobis_grid, cobis_valid_text, etc.) with recommended tools."""
            return _json_out(
                classify_element(
                    {
                        "automation_id": automation_id,
                        "name": name,
                        "class_name": class_name,
                        "role": role,
                    }
                )
            )

        @mcp.tool()
        def cen_list_form_controls(window_title: str = "", max_depth: int = 8) -> str:
            """List visible controls on CEN form with cen_type classification and form context."""
            return _json_out(list_classified_controls(window_title or None, max_depth=max_depth))

        @mcp.tool()
        def cen_detect_form_context(window_title: str = "") -> str:
            """Detect product module, form type, grids and toolbar presence from current window."""
            from tools.ui_automation import do_list_elements

            listed = do_list_elements(window_title=window_title or "", max_depth=4)
            if isinstance(listed, str):
                listed = json.loads(listed)
            return _json_out(
                build_form_context(
                    window_title=listed.get("resolved_window_title") or window_title,
                    elements=listed.get("elements") or [],
                )
            )

        @mcp.tool()
        def cen_get_flow_hint(flow_id: str = "consulta_estandar") -> str:
            """Return recommended MCP tool sequence for a CEN flow (consulta, f5_catalog, cuenta_operacion, etc.)."""
            return _json_out(get_flow_hint(flow_id))

        @mcp.tool()
        def cen_list_flows() -> str:
            """List available CEN automation flow templates from static analysis."""
            return _json_out(list_flows())

        @mcp.tool()
        def cen_set_field(
            automation_id: str = "",
            name: str = "",
            value: str = "",
            window_title: str = "",
        ) -> str:
            """Set COBIS field (txt*/msk*/cbo*) with type-aware handling."""
            return _json_out(
                set_field(automation_id, name, value, window_title or None)
            )

        @mcp.tool()
        def cen_read_field(
            automation_id: str = "",
            name: str = "",
            window_title: str = "",
        ) -> str:
            """Read COBIS field; uses ClipText for masked controls."""
            return _json_out(read_field(automation_id, name, window_title or None))

        @mcp.tool()
        def cen_trigger_f5(
            automation_id: str = "",
            name: str = "",
            window_title: str = "",
        ) -> str:
            """Trigger F5 catalog help on field; waits and reports lookup modal state."""
            return _json_out(trigger_f5(automation_id, name, window_title or None))

        @mcp.tool()
        def cen_select_tab(
            tab_control: str = "MhTab1",
            index: int = 0,
            caption: str = "",
            window_title: str = "",
        ) -> str:
            """Select COBISTabControl page by index or tab caption."""
            return _json_out(select_tab(tab_control, index, caption, window_title or None))

        @mcp.tool()
        def cen_select_radio(
            group_prefix: str = "optVigente",
            index: int = 0,
            caption: str = "",
            window_title: str = "",
        ) -> str:
            """Select radio button array member (optVigente[0]=Si, etc.)."""
            return _json_out(select_radio(group_prefix, index, caption, window_title or None))

        @mcp.tool()
        def cen_outline_select(
            automation_id: str = "otlOficiales",
            text_contains: str = "",
            window_title: str = "",
        ) -> str:
            """Select node in COBISMSOutline hierarchy by partial text."""
            return _json_out(outline_select(automation_id, text_contains, window_title or None))

        @mcp.tool()
        def cen_outline_expand(
            automation_id: str = "otlOficiales",
            window_title: str = "",
        ) -> str:
            """Double-click COBISMSOutline node to expand."""
            return _json_out(outline_expand(automation_id, window_title or None))

        @mcp.tool()
        def cen_detect_dialog(window_title: str = "") -> str:
            """Detect COBISMessageBox / Win32 dialog windows."""
            return _json_out(detect_message_box(window_title or None))

        @mcp.tool()
        def cen_handle_dialog(
            action: str = "ok",
            text_match: str = "",
            window_title: str = "",
        ) -> str:
            """Dismiss dialog with OK/Enter or Cancel/Escape; optional click by button text."""
            return _json_out(handle_dialog(action, text_match, window_title or None))

        @mcp.tool()
        def cen_detect_grid_type(
            automation_id: str = "",
            name: str = "",
            window_title: str = "",
        ) -> str:
            """Detect COBISGrid vs COBISSpread vs UIA table on a grid control."""
            return _json_out(
                detect_cobis_grid(automation_id, name, window_title or None)
            )

        @mcp.tool()
        def cen_read_grid(
            automation_id: str = "",
            name: str = "",
            window_title: str = "",
            offset: int = 0,
            limit: int = 200,
        ) -> str:
            """Read CEN grid as headers+rows (multi-strategy)."""
            return _json_out(
                read_cobis_grid(automation_id, name, window_title or None, offset, limit)
            )

        @mcp.tool()
        def cen_read_grid_cell(
            automation_id: str = "",
            name: str = "",
            row: int = 1,
            column: int = 1,
            window_title: str = "",
        ) -> str:
            """Read one grid cell (1-based by default)."""
            return _json_out(
                read_cobis_grid_cell(automation_id, name, row, column, window_title or None)
            )

        @mcp.tool()
        def cen_select_grid_row(
            automation_id: str = "",
            name: str = "",
            row: int = 1,
            column: int = 1,
            window_title: str = "",
            double_click: bool = False,
        ) -> str:
            """Select grid row by approximate row-band click."""
            return _json_out(
                select_cobis_grid_row(
                    automation_id, name, row, column, window_title or None, double_click
                )
            )

        @mcp.tool()
        def cen_detect_lookup_modal(window_title: str = "") -> str:
            """Detect F5 lookup modal (grid_valoresClass / gr_SQL)."""
            return _json_out(detect_lookup_modal(window_title or None))

        @mcp.tool()
        def cen_search_lookup(search_text: str, window_title: str = "") -> str:
            """Search in lookup modal (txt_comodin + bb_buscar)."""
            return _json_out(search_lookup(search_text, window_title or None))

        @mcp.tool()
        def cen_select_lookup_row(
            row: int = 1,
            window_title: str = "",
            double_click: bool = True,
        ) -> str:
            """Select row in gr_SQL and confirm with bb_escoger."""
            return _json_out(
                select_lookup_row(row, window_title or None, double_click)
            )

        @mcp.tool()
        def cen_list_toolbar(window_title: str = "") -> str:
            """List cmdBoton[] toolbar with index, caption, enabled."""
            return _json_out(list_cobis_toolbar(window_title or None))

        @mcp.tool()
        def cen_click_toolbar(
            index: int = -1,
            caption: str = "",
            window_title: str = "",
        ) -> str:
            """Click toolbar by caption (Buscar/Siguiente) — never assume global index."""
            return _json_out(
                click_cobis_toolbar(index, caption, window_title or None)
            )

        @mcp.tool()
        def cen_detect_modal(window_title: str = "") -> str:
            """Detect active CEN modal type (grid_valores, FBUSCLI, FBUSCONV, message box)."""
            return _json_out(detect_modal(window_title or None))

        @mcp.tool()
        def cen_match_form_profile(window_title: str = "") -> str:
            """Match window against forms catalog (1447+ forms) with toolbar map."""
            from tools.ui_automation import do_list_elements

            listed = do_list_elements(window_title=window_title or "", max_depth=5)
            if isinstance(listed, str):
                listed = json.loads(listed)
            title = listed.get("resolved_window_title") or window_title or ""
            return _json_out(
                match_form_profile(title, listed.get("elements") or [])
            )

        @mcp.tool()
        def cen_grid_pagination(
            automation_id: str = "",
            name: str = "",
            window_title: str = "",
        ) -> str:
            """Check if grid likely has more pages (MaximoRows=19) and Siguiente recommendation."""
            return _json_out(
                grid_pagination_status(automation_id, name, window_title or None)
            )

        @mcp.tool()
        def cen_read_status_hints(window_title: str = "") -> str:
            """Read help/transaction line hints from bottom status area."""
            return _json_out(read_status_hints(window_title or None))

        @mcp.tool()
        def cen_read_toolbar_security(window_title: str = "") -> str:
            """List toolbar buttons with transaction Tag hints from forms_index."""
            return _json_out(read_toolbar_security(window_title or None))

        @mcp.tool()
        def cen_find_controls(
            prefix: str = "",
            cen_type: str = "",
            window_title: str = "",
            max_depth: int = 8,
        ) -> str:
            """Filter controls by name prefix (txt/grd/msk) or cen_type."""
            return _json_out(
                find_controls(prefix, cen_type, window_title or None, max_depth)
            )

        @mcp.tool()
        def cen_suggest_next_action(window_title: str = "") -> str:
            """Agentic helper: suggest next cen_* tool based on form/modal state."""
            return _json_out(suggest_next_action(window_title or None))

        @mcp.tool()
        def cen_list_forms(
            prefix: str = "",
            product: str = "",
            limit: int = 50,
            offset: int = 0,
        ) -> str:
            """List forms from static catalog (filter by prefix FTRAN, product ADM/TAD/REC)."""
            return _json_out(list_forms(prefix, product, limit, offset))

        @mcp.tool()
        def cen_get_form_profile(form_id: str) -> str:
            """Get full toolbar/fields/grids profile for a form id from catalog."""
            return _json_out(get_form_profile(form_id))

        @mcp.tool()
        def cen_search_forms(query: str, limit: int = 20) -> str:
            """Search forms catalog by id substring."""
            return _json_out(search_forms(query, limit))

        @mcp.tool()
        def cen_tristate_list_nodes(
            automation_id: str = "",
            name: str = "",
            window_title: str = "",
        ) -> str:
            """List TreeItem nodes under TriStateTreeView (ADM permisos)."""
            return _json_out(
                list_tristate_nodes(automation_id, name, window_title or None)
            )

        @mcp.tool()
        def cen_tristate_toggle(
            text_contains: str,
            automation_id: str = "",
            name: str = "",
            window_title: str = "",
        ) -> str:
            """Toggle tri-state node by partial label (TVTransaccion, TVRoles, etc.)."""
            return _json_out(
                toggle_tristate_node(
                    automation_id, name, text_contains, window_title or None
                )
            )

        @mcp.tool()
        def cen_toggle_row_visto(
            row: int = 1,
            automation_id: str = "",
            name: str = "",
            visto_column: int = 1,
            window_title: str = "",
        ) -> str:
            """Double-click picVisto column to toggle row selection (FTRAN024)."""
            return _json_out(
                toggle_row_visto(
                    automation_id, name, row, visto_column, window_title or None
                )
            )

        @mcp.tool()
        def cen_open_grid_context(
            automation_id: str = "",
            name: str = "",
            row: int = 1,
            column: int = 1,
            window_title: str = "",
        ) -> str:
            """Right-click COBISSpread grid to open FGrdOpciones context menu."""
            return _json_out(
                open_grid_context_menu(
                    automation_id, name, window_title or None, row, column
                )
            )

        @mcp.tool()
        def cen_grid_context_action(action: str, window_title: str = "") -> str:
            """Click action in grid options popup (Ordenar, Exportar, etc.)."""
            return _json_out(grid_context_action(action, window_title or None))

        @mcp.tool()
        def cen_analyze_form(window_title: str = "", max_depth: int = 6) -> str:
            """One-shot form analysis: profile, modal, toolbar, controls, suggestions."""
            return _json_out(analyze_form(window_title or None, max_depth))

        @mcp.tool()
        def cen_resolve_toolbar(
            intent: str,
            window_title: str = "",
            form_id: str = "",
        ) -> str:
            """Resolve toolbar intent (search/next/exit/transmit) to caption via live UI or catalog."""
            return _json_out(resolve_toolbar_intent(intent, window_title or None, form_id))

        @mcp.tool()
        def cen_click_toolbar_intent(
            intent: str,
            window_title: str = "",
            form_id: str = "",
        ) -> str:
            """Click toolbar by semantic intent — preferred over raw caption."""
            return _json_out(click_toolbar_intent(intent, window_title or None, form_id))

        @mcp.tool()
        def cen_classify_message(text: str) -> str:
            """Classify COBISMessageBox text (validation/confirm/success/security)."""
            return _json_out(classify_message(text))

        @mcp.tool()
        def cen_match_dialog(window_title: str = "") -> str:
            """Read visible dialog text and classify with suggested action."""
            return _json_out(match_dialog_from_ui(window_title or None))

        @mcp.tool()
        def cen_drill_usercontrol(
            automation_id: str = "",
            name: str = "",
            window_title: str = "",
        ) -> str:
            """List children inside cmdMoneda_UserControl / composite UserControl."""
            return _json_out(drill_user_control(automation_id, name, window_title or None))

        @mcp.tool()
        def cen_set_moneda(
            value: str = "",
            index: int = -1,
            user_control: str = "cmdMoneda_UserControl1",
            window_title: str = "",
        ) -> str:
            """Select currency in cmdMoneda_UserControl via cmbMoneda."""
            return _json_out(set_moneda(value, index, user_control, window_title or None))

        @mcp.tool()
        def cen_wait_toolbar_enabled(
            caption: str = "Buscar",
            window_title: str = "",
            timeout_ms: int = 8000,
        ) -> str:
            """Wait until toolbar button enabled (post mskCuenta / Leave RPC)."""
            return _json_out(wait_toolbar_enabled(caption, window_title or None, timeout_ms))

        @mcp.tool()
        def cen_wait_field_stable(
            automation_id: str = "",
            name: str = "",
            window_title: str = "",
            timeout_ms: int = 6000,
        ) -> str:
            """Wait until field value stabilizes after RPC validation."""
            return _json_out(
                wait_field_stable(automation_id, name, window_title or None, timeout_ms=timeout_ms)
            )

        @mcp.tool()
        def cen_catalog_stats() -> str:
            """Stats for forms catalog (count by product, index status)."""
            return _json_out(catalog_stats())

        @mcp.tool()
        def cen_get_popup_hints(form_id: str) -> str:
            """List ShowPopup sub-forms triggered from a host form (static analysis)."""
            return _json_out(get_popup_hints(form_id))

        return 48

    def enrich_control_interaction(
        self,
        element: dict,
        base: dict,
        ctx: AddinContext,
    ) -> dict:
        from detect.classifier import classify_element

        classified = classify_element(element)
        out = dict(base)
        notes = list(out.get("notes") or [])
        if classified.get("notes"):
            notes.append(classified["notes"])
        tools = list(out.get("cen_tools") or [])
        tools.extend(classified.get("mcp_tools") or [])
        if classified.get("f5_capable"):
            notes.append("F5 catalog help available — use cen_trigger_f5")
            tools.append("cen_trigger_f5")
        cen_type = classified.get("cen_type")
        if cen_type == "cobis_tristate_tree":
            tools.extend(["cen_tristate_list_nodes", "cen_tristate_toggle"])
        if cen_type == "cobis_grid_checkbox":
            tools.append("cen_toggle_row_visto")
        if cen_type == "cobis_spread":
            tools.extend(["cen_open_grid_context", "cen_grid_context_action"])
        if cen_type == "cobis_user_control":
            tools.extend(["cen_drill_usercontrol", "cen_set_moneda"])
        if notes:
            out["notes"] = notes
        if tools:
            out["cen_type"] = classified.get("cen_type")
            out["cen_tools"] = sorted(set(tools))
        return out

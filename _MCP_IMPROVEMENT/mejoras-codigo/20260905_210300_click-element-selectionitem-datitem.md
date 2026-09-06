# click_element: cascada SelectionItem para celdas Calendar/DataItem

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-05 21:03:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | tools/ui_automation.py, detection/backends/uia_backend.py |
| **Tool afectada** | click_element, invoke_element |
| **Tipo de gap** | tool_gap |
| **Nivel** | L4 |
| **Impacto** | alto |
| **MCP versión** | v0.2.1 |

## Resumen

**Problema:** En modo Fecha de Calculadora UWP, tras `invoke_element(DateDiff_FromDate)` abre
`CalendarView`. `click_element(name="1", role="DataItem")` encuentra el día pero falla con
«InvokePattern failed; coordinate click skipped for identifiable controls». El agente recurrió a
`element_at_point` + `click(x,y)` manual (229,606 → 255,631). `invoke_element` ya expone cascada
SelectionItem en `uia_backend`, pero `click_element` solo intenta InvokePattern vía
`_try_invoke_click` — no paridad para `DataItem` / `ListItem` / celdas `Calendar`.

**Solución:** En `do_click_element`, antes de rechazar por `_identifiable_by_properties`, intentar
la misma cascada que `invoke_element`: SelectionItem.Select → Toggle → ExpandCollapse (reutilizar
`get_uia_backend().invoke_element` o helper `_try_pattern_activate`). Si SelectionItem OK,
devolver `method: SelectionItemPattern`. Actualizar `control-catalog.md` fila Calendar:
«`invoke_element` o `click_element` con SelectionItem» (no solo click coords).

**Dónde:** `ui_automation.py` (`_try_invoke_click` → `_try_pattern_activate`), tests pytest;
`docs/MCP_TOOLS_REFERENCE.md` § `click_element`.

## Contexto del turno

Turno `calculator_exhaustive_act_verify` — Date mode OBS→ACT→VERIFY: `DateCalculationOption`
expand → Diferencia entre fechas; FromDate 1 sep, ToDate 5 sep → `DateDiffAllUnitsResultLabel`
«4 días» ✓; Sumar/restar días con `AddOption`/`SubtractOption` + `DaysValue` ✓. Única fricción
estructural: selección de día en `CalendarView` sin pattern programático vía `click_element`.
Skills: `awdui-mcp-objective`, `calculator-mcp-harness`. `calculator-lab.md` documenta
DataItem **SelectionItem** pero el agente eligió `click_element` (alineado con catálogo Calendar).

## Cambio propuesto (pseudodiff)

```python
# ui_automation.py
def _try_pattern_activate(elem: dict, window_title: Optional[str] = None) -> Optional[dict]:
    """Invoke → SelectionItem → Toggle → ExpandCollapse (parity invoke_element)."""
    patterns = [str(p).lower() for p in (elem.get("patterns") or [])]
    role = (elem.get("role") or "").lower()
    if "invoke" in patterns or role in ("button", "hyperlink", "menuitem", "splitbutton"):
        inv = do_invoke_on_element(elem, window_title=window_title)
        if inv.get("success"):
            return inv
    if "selectionitem" in patterns or role in ("listitem", "dataitem", "tabitem", "radiobutton"):
        from detection.backends.uia_backend import get_uia_backend
        from detection.element_model import DetectedElement
        detected = DetectedElement(
            name=elem.get("name") or "",
            role=elem.get("role") or "",
            automation_id=elem.get("automation_id") or "",
        )
        return get_uia_backend().invoke_element(detected, window_title=window_title)
    return None

# do_click_element — replace _try_invoke_click call:
pat = _try_pattern_activate(elem, window_title)
if pat and pat.get("success"):
    out = {"success": True, "element": elem, "method": pat.get("method"), ...}
```

```python
# hint when SelectionItem missing but element is calendar cell:
if role == "dataitem" and "selectionitem" not in patterns:
    return {
        "success": False,
        "code": "no_selection_pattern",
        "hint": "Try invoke_element or spy_inspect patterns; calendar cells need SelectionItem",
    }
```

## Verificación de duplicados

- **No duplica** `20260707_014000` (lookup row double-click) — distinto control type y tool.
- **Relacionado** con `121300` ExpandCollapse flyout — misma familia «cascada patterns en act».
- `select_control_item` no existe en servidor v0.2.1; esta propuesta evita nueva tool si
  `click_element`/`invoke_element` cubren SelectionItem.

## Test de abstracción

Cross-app: WinForms `MonthCalendar`, UWP `CalendarView`, `ListItem` en listas, `TabItem`,
`RadioButton` SelectionItem — cualquier celda con SelectionItem sin Invoke.

## Criterio de aceptación

- [ ] `tests/test_click_element_selection_item.py`: mock DataItem con SelectionItem →
      `click_element` success, `method=SelectionItemPattern`, sin coord click.
- [ ] Live Calculadora Date: `click_element(name="1", role="DataItem")` tras abrir FromDate
      sin `element_at_point` ni `click` manual.
- [ ] Sin regresión: Button sigue Invoke primero; identifiable sin pattern sigue error claro.
- [ ] `docs/MCP_TOOLS_REFERENCE.md` § `click_element`: documentar cascada SelectionItem.

## Beneficios futuros

- Modo Fecha y cualquier picker calendario UWP/WinUI sin coords manuales.
- Paridad agente: `click_element` y `invoke_element` intercambiables para SelectionItem.
- Reduce violación de jerarquía AwdUI (coords como último recurso) en celdas UIA identificables.

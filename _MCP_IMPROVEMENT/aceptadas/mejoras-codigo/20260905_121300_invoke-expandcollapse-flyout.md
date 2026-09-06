# invoke_element: cascada ExpandCollapse para flyouts UWP

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | aplicada |
| **Fecha** | 2026-09-05 12:13:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | awdui-spy-sidecar/Program.cs, detection/backends/uia_backend.py, tools/ui_automation.py, tools/spy_bridge.py |
| **Tool afectada** | invoke_element |
| **Tipo de gap** | tool_gap |
| **Nivel** | L4 |
| **Impacto** | alto |

## Resumen

**Problema:** En Calculadora modo Científica, `invoke_element` sobre `trigButton` y
`funcButton` devuelve éxito vacío o error sin abrir el flyout (sin/cos/tan, log/factorial…).
UIA expone estos controles como `Button` / `SplitButton` con **ExpandCollapse** (no Invoke
primario). La cascada actual solo intenta InvokePattern y SelectionItemPattern — en spy
sidecar (`ActivateElement`) y en `uia_backend.invoke_element`.

**Solución:** Extender la cascada de activación en tres capas:
1. **Spy sidecar** `ActivateElement`: tras Invoke/SelectionItem, intentar
   `ExpandCollapse.Expand()` si estado es `Collapsed` o `PartiallyExpanded`; si ya
   `Expanded`, opcional `Collapse()` con param `toggle=true` o devolver
   `already_expanded` + hint `list_elements` hijos flyout.
2. **uia_backend.invoke_element**: misma cascada antes de fallar; reutilizar
   `expand_element` existente como helper interno.
3. **do_invoke_element**: si spy devuelve error «Neither Invoke nor SelectionItem»,
   reintentar con comando sidecar `expand` o segunda pasada con `pattern=expand`.
   Respuesta incluir `method: ExpandCollapse.Expand` y `flyout_opened: true`.

**Dónde:** `Program.cs` (ActivateElement), `uia_backend.py` (invoke_element),
`ui_automation.py` (do_invoke_element mensajes accionables).

## Contexto del turno

**Turno `calc_object_inventory_scientific`:** `launch_app` → `invoke_element` modo
Scientific (SelectionItem, 307 ms) → `list_elements` 48 botones. Constantes y funciones
directas OK: `piButton` 243 ms, `eulerButton` 733 ms, `abs(-5)=` → 5 (218 ms).
`trigButton` y `funcButton`: `invoke_element` falla / respuesta vacía — flyouts no
aparecen en árbol. `clearButton` 700–1000 ms (posible árbol grande + reintentos).
Skills leídas: calculator-mcp-harness, awdui-flow-exploration, awdui-mcp-objective.
MCP v0.2.1.

## Cambio propuesto (pseudodiff)

```csharp
// Program.cs — ActivateElement
static object ActivateElement(AutomationElement elem, bool toggleExpand = false)
{
    if (elem.Patterns.Invoke.IsSupported)
    {
        elem.Patterns.Invoke.Pattern.Invoke();
        return new { success = true, method = "InvokePattern" };
    }
    if (elem.Patterns.SelectionItem.IsSupported)
    {
        elem.Patterns.SelectionItem.Pattern.Select();
        return new { success = true, method = "SelectionItemPattern" };
    }
    if (elem.Patterns.ExpandCollapse.IsSupported)
    {
        var pat = elem.Patterns.ExpandCollapse.Pattern;
        var state = pat.ExpandCollapseState;
        if (state == ExpandCollapseState.Expanded && toggleExpand)
        {
            pat.Collapse();
            return new { success = true, method = "ExpandCollapse.Collapse" };
        }
        if (state != ExpandCollapseState.Expanded)
        {
            pat.Expand();
            return new { success = true, method = "ExpandCollapse.Expand", flyout_opened = true };
        }
        return new { success = true, method = "ExpandCollapse", state = "Expanded",
                     hint = "Flyout already open; list_elements for MenuItem/Button children" };
    }
    return new { success = false, error = "No Invoke, SelectionItem, or ExpandCollapse" };
}
```

```python
# uia_backend.py — invoke_element pattern cascade
def _invoke_pattern_cascade(raw_element) -> dict:
    from pywinauto.uia_defines import get_elem_interface
    el = raw_element.element_info.element
    for name, fn in [
        ("Invoke", lambda: get_elem_interface(el, "Invoke").Invoke()),
        ("ExpandCollapse", lambda: _expand_if_collapsed(el)),
        ("SelectionItem", lambda: get_elem_interface(el, "SelectionItem").Select()),
        ("Toggle", lambda: get_elem_interface(el, "Toggle").Toggle()),
    ]:
        try:
            fn()
            return {"success": True, "method": f"{name}Pattern"}
        except Exception:
            continue
    return {"success": False, "error": "No supported activation pattern"}
```

```python
# ui_automation.py — enrich failure from spy
if not spy.get("success") and "ExpandCollapse" in (spy.get("patterns") or []):
    # retry expand via uia_backend.expand_element(automation_id=...)
```

## Verificación de duplicados

- No hay propuesta abierta sobre ExpandCollapse en invoke (distinto de `list_combo_items`
  aceptada que usa Expand en combo WinForms).
- `control-catalog.md` ya documenta ExpandCollapse en SplitButton — gap es **código**,
  no skill routing.
- `invoke_pattern` referenciada en docs pero no implementada en servidor; esta propuesta
  cubre el caso flyout vía `invoke_element` sin nueva tool.

## Test de abstracción

Aplica a cualquier UWP/WinUI `SplitButton`, menús ToolBar expandibles, TreeItem,
ComboBox cerrado (complementa `repo_action` Select) — no sintoma puntual Calculadora.

## Criterio de aceptación

- [ ] `tests/test_invoke_expandcollapse.py`: mock elemento con solo ExpandCollapse →
      `invoke_element(automation_id="trigButton")` devuelve `method=ExpandCollapse.Expand`.
- [ ] Test spy sidecar unit o integration stub: ActivateElement con ExpandCollapse only.
- [ ] Live Calculadora Científica: `invoke_element(trigButton)` → flyout visible;
      `list_elements` incluye `sinButton`/`cosButton`/`tanButton` (o nombres ES).
- [ ] `invoke_element(funcButton)` → flyout con log/factorial/etc.
- [ ] Documentar en `MCP_TOOLS_REFERENCE.md` cascada Invoke → ExpandCollapse → SelectionItem.
- [ ] `docs/AGENT_GUIDE.md`: flyout UWP → `invoke_element` (no coords) tras este fix.

## Beneficios futuros

- Inventario Científica completo sin OCR/coords en trig/func.
- Patrón reutilizable para ToolBar, NavView submenús, SplitButton WinUI.
- Errores accionables (`flyout_opened`, `already_expanded`) en lugar de invoke vacío.

## Nota post-implementación (2026-09-05 12:16)

**Aplicada con variante TogglePattern** (no ExpandCollapse): `trigButton`/`funcButton`
en Calculadora UWP exponen `TogglePattern`, no ExpandCollapse. Fix en
`Program.cs` `ActivateElement` + cascada `uia_backend.invoke_element`;
`test_spy_invoke_selection.py` 6 passed; flyouts y `sin(0)=0` verificados.
Mantenedor: marcar `Estado: aplicada` y archivar; ExpandCollapse en cascada
sigue siendo mejora opcional para TreeItem/Combo (no bloqueante Calculadora).

## Evidencia adicional — turno calc_object_inventory_converters (2026-09-05 12:26)

**App:** Calculadora UWP — modos Date, Currency, Volume, Length (`calc_object_inventory_converters`).

**Éxitos UIA (sin coords):** `DateCalculationOption` vía SelectionItem (387 ms);
`DateDiff_FromDate` Invoke → `CalendarView` DataItem día 1 → `DateDiffAllUnitsResultLabel`
«Diferencia: 4 días»; Currency numpad 100 → `Value2` «86,10 Europa Euro»;
`CurrencyRefreshBlock` Invoke (271 ms); Volume 5 tsp → 24,64461 ml; Length 1 in → 2,54 cm.

**Gap reconfirmado (tool_gap L4):** ComboBox `Units1`, `Units2`, `DateCalculationOption`
exponen **ExpandCollapse** (no Invoke primario). `invoke_element` falla al intentar
abrir picker de unidades / opción de cálculo de fecha. Documentado en
`patterns/calculator-lab.md` § Conversores.

**Workaround del turno:** inventario marcado `met` verificando conversión vía `Value1`/`Value2`
sin enumerar items del dropdown. Bloquea inventario completo de opciones de unidad
(EUR↔USD picker, tsp↔ml lista, `DateCalculationOption` items).

**Relación con TogglePattern (Científica):** flyouts trig/func resueltos con Toggle;
conversores requieren **ExpandCollapse** en cascada — caso distinto, misma propuesta.

**Routing:** `control-catalog.md` indica `invoke_pattern(ExpandCollapse)` pero esa tool
no está implementada en servidor v0.2.1; el agente recurrió a `invoke_element` → fallo
predecible. Fix en cascada `invoke_element` (o implementar `invoke_pattern`) desbloquea
combos UWP/WinUI además de TreeItem.

**Prioridad:** sube a **bloqueante** para `calculator_perfect` en modos conversores
(settings pendiente en `state.json`).

## Evidencia adicional — turno docs_tools_sync (2026-09-05 12:33)

**Turno:** Mantenimiento catálogo tools — 59 tools reales, 26 fantasma removidas;
`validate_tools_reference` + pytest OK.

**Catálogo:** `MCP_TOOLS_REFERENCE.md` changelog y sección `invoke_element` documentan explícitamente
gap **ExpandCollapse** (ComboBox conversores) y **SettingsExpander** (click header). Refuerza
prioridad bloqueante sin nuevo gap.

**Live:** `clearButton` `invoke_element` **277 ms** — InvokePattern estándar OK; no relacionado
con ExpandCollapse pero confirma baseline de performance tras sync docs.

**Pendiente implementación:** cascada ExpandCollapse en `invoke_element` / tool `expand_element`
(sibling `20260905_123100`) sigue siendo el remedio; docs ya no prometen `invoke_pattern`.

## Post-implementación — turno `mcp_expand_element_tool` (2026-09-05 12:36)

**Aplicado:**
- Cascada `invoke_element`: Invoke → Toggle → SelectionItem → **ExpandCollapse.Expand**
  (`uia_backend.py`; test `test_uia_invoke_chain_includes_expand_collapse`).
- Spy `ActivateElement` incluye ExpandCollapse tras Toggle/SelectionItem.
- Tool dedicada `expand_element` con spy-first en UWP (`do_expand_element`).

**Live conversores (desbloqueado):** `Units1` 264 ms, `DateCalculationOption` 405 ms — picker
visible sin coords. Gap conversores **cerrado** para `calculator_perfect`.

**Mantenedor:** marcar `Estado: aplicada` y archivar. TogglePattern (Científica) ya aplicado
12:16; ExpandCollapse (conversores) cerrado en este turno. SettingsExpander queda en
`20260905_123601_settings-expander-fallback-click.md`.

## Evidencia adicional — turno calc_object_inventory_settings (2026-09-05 12:31)

**App:** Calculadora UWP — panel Configuración (`SettingsItem`).

**Éxitos UIA (sin coords):** `SettingsItem` Invoke 264 ms; theme radios
`LightThemeRadioButton` / `DarkThemeRadioButton` / `SystemThemeRadioButton` vía
SelectionItem (DarkTheme verificado 337 ms); `FeedbackButton` Invoke 278 ms;
`AboutBuildVersion` `11.2607.0.0`; `BackButton` Invoke 243 ms → Longitud.

**Gap SettingsExpander (distinto de ExpandCollapse):** `AppThemeExpander` y
`AboutExpander` (rol Group / SettingsExpander) **no exponen** Invoke ni
ExpandCollapse — expandir requirió **click en header** (workaround). Propuesta
complementaria: tool `expand_element` con `fallback_click` (ver
`20260905_123100_expand-element-automation-id.md`).

**ComboBox ExpandCollapse:** sigue bloqueante en conversores (`Units1`, `Units2`,
`DateCalculationOption`); este turno settings no usa combos pero el gap persiste
para `calculator_perfect`.

**Relación:** TogglePattern resuelve flyouts Científica; ExpandCollapse en cascada
resuelve ComboBox conversores; SettingsExpander necesita fallback click en tool
`expand_element` o heurística en `click_element` con hint de rol.

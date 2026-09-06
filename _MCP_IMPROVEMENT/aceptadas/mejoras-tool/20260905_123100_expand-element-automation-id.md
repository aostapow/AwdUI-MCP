# Tool expand_element / collapse_element

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_tool |
| **Estado** | aplicada |
| **Fecha** | 2026-09-05 12:31:00 |
| **Usuario sesión** | ariel.ostapow |
| **Tool afectada** | (nueva) expand_element, collapse_element |
| **Módulo** | detection/backends/uia_backend.py, tools/ui_automation.py, server.py |
| **Tipo de gap** | tool_gap |
| **Nivel** | L4 |
| **Impacto** | alto |

## Resumen

**Problema:** `uia_backend.expand_element` / `collapse_element` existen pero **no están
expuestos** como tools MCP. El agente solo tiene `invoke_element` (sin ExpandCollapse en
cascada v0.2.1) o `click_element` como workaround. En Calculadora Settings,
`AppThemeExpander` y `AboutExpander` (rol `SettingsExpander` / Group) **no exponen**
Invoke ni ExpandCollapse — el turno `calc_object_inventory_settings` expandió vía
**click en header** (gap documentado). En conversores, ComboBox `Units1`/`Units2` y
`DateCalculationOption` sí exponen ExpandCollapse pero `invoke_element` falla (propuesta
código `20260905_121300`). `control-catalog.md` y `MCP_TOOLS_REFERENCE.md` documentan
`invoke_pattern(ExpandCollapse)` pero **esa tool no está implementada** en servidor.

**Solución:** Exponer tools atómicas `expand_element` y `collapse_element` con resolución
por `automation_id` (además de name/role), reutilizando backend existente:

1. **ExpandCollapse primario:** `Expand()` / `Collapse()`; respuesta
   `{ success, method, expand_state }`.
2. **Fallback header-click (opcional `fallback_click=true`):** si el control no tiene
   ExpandCollapse pero rol contiene `Expander` o `SettingsExpander`, o
   `automation_id` termina en `Expander`, hacer `click_element` en el tercio superior
   del bounding rect (chevron/header UWP).
3. Integrar como paso interno de `invoke_element` cascada (ver propuesta código
   `20260905_121300` — complementaria, no duplicada).

**Dónde:** `ui_automation.py` (handlers), `uia_backend.py` (añadir
`automation_id` a `expand_element`), `server.py` (registro), `MCP_TOOLS_REFERENCE.md`.

## Contexto del turno

**Turno `calc_object_inventory_settings`:** `SettingsItem` Invoke 264 ms → panel
Configuración. `AppThemeExpander`: sin Invoke/ExpandCollapse → **click** para expandir
(gap). `LightThemeRadioButton` / `DarkThemeRadioButton` / `SystemThemeRadioButton`:
SelectionItem OK; DarkTheme verificado 337 ms. `FeedbackButton` Invoke 278 ms.
`AboutBuildVersion` `11.2607.0.0`; `AboutExpander` expand vía click → links
`AboutEULA`, `AboutControlServicesAgreement`, `AboutControlPrivacyStatement`.
`BackButton` Invoke 243 ms → vuelve a Longitud. Screenshots `_12.._16.png`.
Skills: `awdui-mcp-objective`, `calculator-mcp-harness`. MCP v0.2.1.

**Gaps explícitos del turno:** SettingsExpander sin Invoke; ComboBox ExpandCollapse
(bloqueante conversores, reconfirmado).

## Spec propuesta

```json
{
  "name": "expand_element",
  "parameters": {
    "automation_id": "optional — preferido",
    "name": "optional",
    "role": "optional",
    "window_title": "optional",
    "fallback_click": "bool, default false — click header si sin ExpandCollapse",
    "toggle": "bool, default false — collapse si ya expanded"
  }
}
```

```json
{
  "name": "collapse_element",
  "parameters": {
    "automation_id": "optional",
    "name": "optional",
    "role": "optional",
    "window_title": "optional"
  }
}
```

**Comportamiento `expand_element`:**
1. Resolver por `automation_id` → name/role (mismo orden que `invoke_element`).
2. Si ExpandCollapse soportado: `Expand()` si `Collapsed`/`PartiallyExpanded`; si
   `Expanded` y `toggle=true` → `Collapse()`.
3. Si sin ExpandCollapse y `fallback_click=true` y rol/id sugiere expander UWP →
   `click_element` en `(center_x, top + height/6)` del rect.
4. Respuesta: `{ success, method, expand_state?, used_fallback_click? }`.

**Errores accionables:** `no_expand_pattern` + hint `fallback_click=true` o
`spy_inspect` patterns.

## Verificación de duplicados

- **Complementa** `20260905_121300_invoke-expandcollapse-flyout.md` (cascada en
  `invoke_element`); esta propuesta expone operación explícita y fallback SettingsExpander.
- **No duplica** `list_combo_items` aceptada (lista items tras expandir).
- `invoke_pattern` documentada pero ausente — implementar vía `expand_element` o alias
  `invoke_pattern(pattern="ExpandCollapse", action="expand")`.

## Test de abstracción

Cross-app: TreeItem, ComboBox UWP/WinUI, MenuItem, SettingsExpander UWP, NavView
expanders — no sintoma puntual Calculadora.

## Criterio de aceptación

- [ ] `tests/test_expand_element.py`: mock ExpandCollapse only → `method=ExpandCollapse.Expand`.
- [ ] Mock SettingsExpander sin pattern + `fallback_click=true` → click en header rect.
- [ ] Live Calculadora Settings: `expand_element(automation_id="AppThemeExpander", fallback_click=true)` → hijos `ThemeRadioButtons` visibles.
- [ ] Live conversores: `expand_element(automation_id="Units1")` sin fallback → picker unidades.
- [ ] Documentado en `MCP_TOOLS_REFERENCE.md`; deprecar o implementar `invoke_pattern`.
- [ ] Retirar o marcar «pendiente MCP» referencias a `invoke_pattern` / combo tools fantasma en
      `docs/AGENT_GUIDE.md` y `patterns/control-catalog.md` (drift post docs_tools_sync).
- [ ] `calculator-lab.md` § Configuración: reemplazar «click manual» por `expand_element`.

## Beneficios futuros

- Agente no improvisa coords para expanders UWP sin pattern.
- ComboBox/Tree expand explícito sin side effects de Invoke.
- Puente hasta cascada completa en `invoke_element`; API estable para `list_control_items`.

## Evidencia adicional — turno docs_tools_sync (2026-09-05 12:33)

**Turno:** Sincronización `docs/MCP_TOOLS_REFERENCE.md` con código (`validate_tools_reference` OK,
`test_tools_reference` 1 passed). Índice reducido a **59 tools reales**; **26 entradas fantasma**
removidas (incl. `invoke_pattern` y otras no registradas en `server.py`).

**Gap documentado en catálogo:** sección `invoke_element` anota ComboBox `ExpandCollapse` y
`SettingsExpander` sin pattern → workaround `click` en header. Alineado con esta propuesta.

**Drift residual (routing_tool L3):** `docs/AGENT_GUIDE.md` y
`patterns/control-catalog.md` **siguen** referenciando `invoke_pattern` y tools de combo/grilla
como disponibles. Criterio de aceptación ampliado: al exponer `expand_element`, retirar o marcar
«pendiente MCP» esas referencias fantasma en AGENT_GUIDE + control-catalog (no solo
`MCP_TOOLS_REFERENCE.md`).

**Live post-sync:** `launch_app` Calculadora → `invoke_element(clearButton)` enabled, **277 ms**
(mejor que 700–1000 ms en inventarios previos; posible efecto dedup/stale-cache).

## Post-implementación — turno `mcp_expand_element_tool` (2026-09-05 12:36)

**Aplicado en código (MCP v0.2.1):**
- Tool `expand_element` registrada en `server.py` / `ui_automation.py`.
- Spy sidecar comando `expand_collapse` (`Program.cs` `ExpandCollapseCmd`).
- Cascada `invoke_element` incluye ExpandCollapse (`uia_backend.invoke_element`).
- `tests/test_expand_element.py`: **3 passed** (spy bridge, UWP spy-first, invoke chain).
- `docs/MCP_TOOLS_REFERENCE.md` actualizado (59 tools, changelog 2026-09-05).

**Live verificado:**
- `expand_element(automation_id="Units1")` → lista monedas, **264 ms**.
- `expand_element(automation_id="DateCalculationOption")` → modos fecha, **405 ms**.

**Pendiente de esta propuesta (no archivar aún):**
- [ ] Parámetro `fallback_click` para `SettingsExpander` (`AppThemeExpander`, `AboutExpander`).
- [ ] Tool hermana `collapse_element` o documentar `action=collapse` como suficiente.
- [ ] Criterios live Settings + drift `AGENT_GUIDE` / `control-catalog` (ver propuesta skill
      `20260905_123600_control-catalog-expand-element-routing.md`).

**Mantenedor:** marcar `Estado: aplicada` solo tras `fallback_click` o abrir propuesta código
sibling `20260905_123601_settings-expander-fallback-click.md` y archivar el núcleo de esta spec.

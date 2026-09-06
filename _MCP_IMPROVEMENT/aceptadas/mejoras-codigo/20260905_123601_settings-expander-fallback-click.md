# expand_element: fallback_click para SettingsExpander UWP

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | aplicada |
| **Fecha** | 2026-09-05 12:36:01 |
| **Usuario sesión** | ariel.ostapow |
| **Tool afectada** | expand_element |
| **Módulo** | tools/ui_automation.py, tools/input_tools.py (click header rect) |
| **Tipo de gap** | tool_gap |
| **Nivel** | L4 |
| **Impacto** | medio |

## Resumen

**Problema:** Tras implementar `expand_element` con ExpandCollapse (turno
`mcp_expand_element_tool`, tests 3 passed, live `Units1`/`DateCalculationOption` OK),
los controles `AppThemeExpander` y `AboutExpander` en Calculadora Configuración **siguen sin**
Invoke ni ExpandCollapse (rol `SettingsExpander` / Group). El agente debe usar **click manual**
en el header — único gap restante del inventario settings para `calculator_perfect`.

**Solución:** Extender `do_expand_element` con parámetro opcional `fallback_click: bool = false`:

1. Tras fallo spy + UIA ExpandCollapse, si `fallback_click=true` y heurística expander:
   - `automation_id` termina en `Expander`, o
   - `role` contiene `Expander` / `SettingsExpander`, o
   - `spy_inspect` patterns vacío y rol `Group` con hijos colapsados.
2. Resolver bounding rect del control → `click_element` en `(center_x, top + height/6)`.
3. Respuesta: `{ success, method: "HeaderClick", used_fallback_click: true, expand_state? }`.
4. Error accionable si sin pattern y `fallback_click=false`:
   `no_expand_pattern` + hint `fallback_click=true` o `click` en header.

**Dónde:** `ui_automation.py` (`do_expand_element`, tool wrapper param),
`MCP_TOOLS_REFERENCE.md` nota SettingsExpander, `calculator-lab.md` § Configuración.

## Contexto del turno

**Turno `mcp_expand_element_tool`:** nueva tool `expand_element`; invoke chain ExpandCollapse;
spy `expand_collapse`; live Units1 264 ms (monedas), DateCalculationOption 405 ms; pytest 3
passed. Skills: `awdui-mcp-objective`, `calculator-mcp-harness`. MCP v0.2.1.

**Gap explícito:** SettingsExpander sin pattern — documentado en `MCP_TOOLS_REFERENCE.md` y
`calculator-lab.md` como click manual; no resuelto por `expand_element` actual.

## Cambio propuesto (pseudodiff)

```python
# ui_automation.py — do_expand_element
def do_expand_element(..., fallback_click: bool = False) -> dict:
    ...
    if not success and fallback_click and _looks_like_uwp_expander(detected):
        rect = _element_rect(detected, window_title)
        if rect:
            cx = (rect.left + rect.right) // 2
            cy = rect.top + max(1, (rect.bottom - rect.top) // 6)
            click_result = do_click_element_at(cx, cy, window_title=window_title)
            return _finish({
                "success": click_result.get("success", True),
                "method": "HeaderClick",
                "used_fallback_click": True,
            })
    return _finish({"success": False, "error": "...", "hint": "fallback_click=true"})
```

## Verificación de duplicados

- **Remanente** de `20260905_123100_expand-element-automation-id.md` (núcleo expand_element
  ya aplicado; archivar 123100 tras este fix o marcar 123100 aplicada con sibling abierto).
- No duplica TogglePattern Científica ni ExpandCollapse ComboBox (ya resueltos).

## Test de abstracción

Cross-app: NavView expanders WinUI, Settings panels UWP sin ExpandCollapse pattern,
cualquier `*Expander` automation_id — no sintoma puntual Calculadora.

## Criterio de aceptación

- [ ] `tests/test_expand_element.py`: mock SettingsExpander sin ExpandCollapse +
      `fallback_click=true` → `method=HeaderClick`, click en tercio superior del rect.
- [ ] Live Calculadora: `expand_element(automation_id="AppThemeExpander", fallback_click=true)`
      → hijos `LightThemeRadioButton` visibles.
- [ ] Live: `AboutExpander` + `fallback_click=true` → links `AboutEULA` en árbol.
- [ ] `MCP_TOOLS_REFERENCE.md`: documentar param `fallback_click`.
- [ ] `calculator-lab.md` § Configuración: reemplazar «click manual» por `expand_element(..., fallback_click=true)`.

## Beneficios futuros

- Settings Calculadora 100% programático sin coords improvisadas.
- Patrón reutilizable para expanders WinUI opacos a UIA patterns.
- Cierra último gap settings para `calculator_perfect`.

## Evidencia adicional — turno `calculator_perfect_eval` (2026-09-05 12:39)

**App:** Calculadora UWP — evaluación ciclo OBSERVAR→ACTUAR→VERIFICAR (`state.json`
`current_focus=settings_expander_gap`).

**Éxitos previos al gap:**
- `launch_app` PID 16624 + `set_target_window` Calculadora.
- `spy_inspect(clearButton)` → `is_enabled=true` (instancia huérfana mitigada con relaunch;
  ver evidencia parcial en `20260905_120902`).
- Estándar: `num1`/`num2`/`multiply`/`num8`/`equal` Invoke 456–486 ms →
  `CalculatorResults` «Se muestra 96»; screenshot `awdui_1788622657120_1.png`.
- Settings: `TogglePane` + `SettingsItem` SelectionItem **576 ms** (panel Configuración OK).

**Gap reconfirmado (bloqueante `calculator_perfect`):**
- `expand_element(automation_id="AppThemeExpander")` → **ExpandCollapse not supported**
  (rol SettingsExpander/Group sin pattern).
- `find_element` confirma `automation_id=AppThemeExpander` — detección OK, activación falla.
- Agente usó routing correcto (`expand_element` antes de coords); falta param
  `fallback_click=true` de esta propuesta.

**state.json:** `calculator_perfect_eval` done; `blockers` vacío;
`blockers_mitigated=huérfana`; inventario partial por SettingsExpander.
**Prioridad:** **bloqueante único** restante para `calculator_perfect` (MCP v0.2.1).

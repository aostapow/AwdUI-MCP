# expand_element: fast-path cuando fallback_click=true

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | aplicada |
| **Fecha** | 2026-09-05 12:45:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | tools/ui_automation.py, tools/spy_bridge.py |
| **Tool afectada** | expand_element |
| **Tipo de gap** | performance |
| **Nivel** | L4 |
| **Impacto** | alto |
| **MCP versión** | v0.2.1 |

## Resumen

**Problema:** Tras aplicar `fallback_click` para `SettingsExpander` (propuesta
`20260905_123601`, tests 7 passed, live OK), `expand_element` con
`fallback_click=true` tarda **~17–18 s** por expander (`AppThemeExpander` 18546 ms,
`AboutExpander` 17612 ms). El mismo turno muestra ExpandCollapse nativo en
`Units1`/`DateCalculationOption` en **264–405 ms**. El agente paga el costo de
spy + UIA ExpandCollapse (dos intentos) y `spy_inspect` antes del header click,
aunque el control **no tiene** pattern y la heurística `_looks_like_uwp_expander`
ya es conocible por `automation_id`.

**Solución:** Cuando `fallback_click=true`, resolver el elemento con un find ligero
(`spy_inspect` o `do_find_element` con cache) y, si `_looks_like_uwp_expander`,
**saltar** la cadena ExpandCollapse (spy + UIA + segundo spy) e ir directo a
`_expand_element_fallback_header_click`. Opcional: timeout corto (≤500 ms) en
intentos Expand cuando `fallback_click` está activo.

**Dónde:** `do_expand_element` en `ui_automation.py`; documentar en
`MCP_TOOLS_REFERENCE.md` § `expand_element` nota de performance.

## Contexto del turno

Turno `settings_expander_gap`: implementado `fallback_click` + `element_screen_bbox`
header; pytest `test_expand_element` 7 passed; live `LightThemeRadioButton` y
`AboutEULA` verificados; screenshots `awdui_1788623054740_1.png`,
`awdui_1788623096971_2.png`. Skills: `awdui-mcp-objective`, `calculator-mcp-harness`.
`state.json` marca gap cerrado pero deja `expand_element fallback_click lento (~17s)`
en `calculator_perfect_gaps`.

## Cambio propuesto (pseudodiff)

```python
# ui_automation.py — do_expand_element, tras validar Windows
def do_expand_element(..., fallback_click: bool = False) -> dict:
    ...
    # Fast-path: caller already knows pattern is absent (SettingsExpander, etc.)
    if fallback_click and (automation_id or name):
        elem_dict = _quick_resolve_element(automation_id, name, window_title)
        if elem_dict and _looks_like_uwp_expander(elem_dict):
            return _finish(_expand_element_fallback_header_click(elem_dict, window_title))

    # Existing chain: detect_framework → spy expand → find → uia expand → spy → inspect → fallback
    ...
```

```python
def _quick_resolve_element(automation_id, name, window_title) -> Optional[dict]:
    """spy_inspect or cached find — no ExpandCollapse attempts."""
    from tools.spy_bridge import spy_inspect_element, spy_props_to_element
    props = spy_inspect_element(
        name=name, automation_id=automation_id, window_title=window_title,
    )
    if props.get("found"):
        return spy_props_to_element(props.get("properties") or props, window_title=window_title)
    matches = do_find_element(..., include_offscreen=True)
    return matches["elements"][0] if matches.get("found") else None
```

**Respuesta:** incluir `fast_path: true` cuando se omitió la cadena ExpandCollapse.

## Verificación de duplicados

- Complementa `20260905_123601` (aplicada — funcionalidad); no duplica.
- Distinto de `observe-ui-depth-cap` (observe_ui_tool), aunque mismo `tipo_gap`.
- Sin propuesta abierta previa sobre latencia de `expand_element`.

## Test de abstracción

Cross-app: cualquier UWP/WinUI `*Expander` sin ExpandCollapse (Configuración, flyouts
custom) se beneficia; no es síntoma solo de Calculadora.

## Criterio de aceptación

- [ ] `tests/test_expand_element.py`: mock SettingsExpander + `fallback_click=true` →
      `elapsed_ms` < 2000 (ideal < 500) sin llamar `spy_expand_collapse`.
- [ ] Live Calculadora: `expand_element(AppThemeExpander, fallback_click=true)` < 1 s.
- [ ] Sin regresión: `Units1` sin `fallback_click` sigue usando ExpandCollapse (~300 ms).
- [ ] `MCP_TOOLS_REFERENCE.md`: nota «use `fallback_click` para expanders sin pattern;
      fast-path evita reintentos ExpandCollapse».

## Beneficios futuros

- Ciclo OBSERVAR→ACTUAR en Configuración Calculadora usable en tiempo agentico.
- Menos riesgo de timeout en flujos con varios expanders consecutivos.
- Patrón reutilizable para otros fallbacks «pattern ausente, click alternativo».

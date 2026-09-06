# Verificación display científica con lectura UIA stale

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-05 13:02:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | tools/ui_automation.py, tools/spy_bridge.py, detection/orchestrator.py |
| **Tool afectada** | get_element_properties, spy_inspect, invoke_element |
| **Tipo de gap** | deteccion |
| **Nivel** | L4 |
| **Impacto** | alto |
| **MCP versión** | v0.2.1 (up to date) |

## Resumen

**Problema:** En modo Científica, `invoke_element` sobre `cosButton`/`tanButton` devolvió
`success=true` pero la verificación vía `CalculatorExpression` mostró **«0=»** sin token
de función (`cos`, `tan`). En el mismo turno `sinButton` sí devolvió `code=stale_instance`.
El pre-flight `_stale_instance_probe` aplica al **invoke** pero no a la **lectura** de
display (`get_element_properties` / `spy_inspect` sobre `CalculatorExpression` o
`CalculatorResults`), permitiendo falsos positivos de verificación con árbol huérfano.

**Solución:** (1) Reutilizar `spy_verify_live` / `_stale_instance_probe` en
`do_get_element_properties` y en respuestas de `spy_inspect` cuando el target es display
(`CalculatorResults`, `CalculatorExpression`, `Header`). (2) Nuevo helper
`read_display_snapshot(window_title)` que devuelve `{results, expression, process_id, live}`.
(3) Tras `invoke_element` en botones científicos unarios, opcional `verify_display_delta`:
comparar `CalculatorResults.name` antes/después; si invoke OK pero display sin cambio y
PID mismatch → `code=stale_display_read`. (4) Integrar `wait_for_change(threshold=0.002)`
corto (≤1s) solo si lectura inicial `live=true` y delta pendiente.

**Dónde:** `ui_automation.py`, `spy_bridge.py`; documentar en `MCP_TOOLS_REFERENCE.md`.

## Contexto del turno

Turno `calculator_exhaustive_act_verify`: Estándar verificado (÷, ×, historial+LightDismiss).
Intento Científica: cos/tan invoke OK, expresión «0=»; sinButton stale_instance. MCP
`Connection closed` mid-session; restart `AWDUI_RESTART=1788624058`. Skills:
`awdui-mcp-objective`, `calculator-mcp-harness`.

## Cambio propuesto (pseudodiff)

```python
# ui_automation.py — display automation_ids (Calculadora UWP; extensible por hint)
_DISPLAY_AIDS = frozenset({
    "CalculatorResults", "CalculatorExpression", "Header",
})

def do_get_element_properties(automation_id, window_title=None, ...):
    if automation_id in _DISPLAY_AIDS:
        stale = _stale_instance_probe(automation_id, window_title)
        if stale:
            return {**stale, "found": False, "display_read": True}
    # ... existing path
```

```python
# spy_bridge.py
def read_display_snapshot(window_title: str | None = None) -> dict:
    out = {}
    for aid in ("CalculatorResults", "CalculatorExpression"):
        live = spy_verify_live(aid, window_title, require_enabled=False)
        if not live.get("live"):
            return {"live": False, "code": "stale_display_read", "failed_aid": aid}
        hit = spy_inspect_element(automation_id=aid, window_title=window_title)
        out[aid] = (hit.get("properties") or {}).get("name", "")
        out["process_id"] = live.get("process_id")
    out["live"] = True
    return out
```

```python
# ui_automation.py — post-invoke optional verify (scientific unary buttons)
_SCI_UNARY = frozenset({
    "sinButton", "cosButton", "tanButton", "logButton", "sqrtButton", ...
})

def do_invoke_element(..., verify_display: bool = False):
    before = read_display_snapshot(window_title) if verify_display else None
    result = ...  # existing invoke + stale probe
    if verify_display and result.get("success") and automation_id in _SCI_UNARY:
        after = read_display_snapshot(window_title)
        if not after.get("live"):
            return {**after, "invoke": result, "hint": "relaunch calc before verify"}
        if before and after.get("CalculatorResults") == before.get("CalculatorResults"):
            return {
                "success": False,
                "code": "display_unchanged",
                "invoke": result,
                "before": before,
                "after": after,
                "hint": "stale tree or wrong pattern; spy_inspect + relaunch",
            }
    return result
```

## Verificación de duplicados

- **Consolidar con** `20260905_120902_stale-element-cache-invalidate.md` (mismo root cause:
  lectura display sin probe). Esta propuesta **especifica** el contrato display-read +
  verify delta científica; no reemplaza invalidación cache global.
- Distinto de flyout TogglePattern (`121301`) — cos/tan aquí son botones directos del teclado.

## Test de abstracción

Cualquier app con campo resultado + expresión (editores, conversores) se beneficia de
`read_display_snapshot` con `verify_live` — no sintoma Calculadora puntual.

## Criterio de aceptación

- [ ] `tests/test_display_read_stale.py`: mock PID mismatch en `CalculatorExpression` →
      `get_element_properties` devuelve `code=stale_instance` sin name huérfano.
- [ ] `tests/test_scientific_verify_delta.py`: invoke OK + results sin cambio →
      `code=display_unchanged`.
- [ ] Live Calculadora: `cosButton` con display en 0 → results «1» o expression contiene
      `cos` tras invoke + verify.
- [ ] Documentado en `MCP_TOOLS_REFERENCE.md` parámetro `verify_display` en `invoke_element`.

## Beneficios futuros

- Científica deja de marcar «invoke OK» con verificación falsa «0=».
- Agente recibe señal unificada stale en actuar y en leer display.
- Menos confusión post-`Connection closed` MCP al forzar health read antes de continuar.

## Evidencia adicional — turno cierre trig (2026-09-05 13:05)

**Protocolo correcto confirmado:** `trigButton` On → `cosButton`/`tanButton` (sin `num0`) →
`CalculatorExpression` «grados de coseno (0)» / «grados de tangente (0)» → `equalButton` →
`CalculatorResults` 1 / 0. El falso negativo «0=» del turno anterior era secuencia
`cos`→`0`→`=` (routing/ejecución), no fallo de invoke.

**Stale residual:** `sinButton` → `code=stale_instance` tras `clearButton` con flyout trig
abierto; `cosButton`/`tanButton` invoke OK en misma sesión. Refuerza lectura display con
`verify_live` y evitar `clearButton` entre funciones del mismo flyout (documentado en skill).

**Prioridad código sin cambio:** skill ya guía verify; propuesta sigue válida para
`read_display_snapshot` + `stale_display_read` automático en MCP v0.2.1+.

## Evidencia adicional — turno exhaustive sec/csc/cot (2026-09-05 13:06)

**Verificación OK con workaround:** sec(0)=1, csc(0)=0, cot(0)=0 vía `funcButton`→`equalButton`
sin `num0`; display leído correctamente **tras relaunch por función** (no encadenado sin relaunch).

**Refuerza gap código:** el workaround `launch_app` entre funciones confirma que invoke/display
pueden ser válidos en una pasada y stale en la siguiente tras `equalButton` — el agente no debería
depender de relaunch manual; `verify_display_delta` + `stale_display_read` en lectura post-`equalButton`
reducirían fricción en inventarios trig completos (6+ funciones).

**Sin falso negativo «0=»:** patrón func→= aplicado correctamente; no hubo lectura expression huérfana
en este turno (contraste con turno 13:02 cos/tan).

## Evidencia adicional — turno trig flyout 17/17 (2026-09-05 20:42)

**Verificación con `verify_name_contains` genérico:** act+verify de invsec/invcsc/invcot usó
needle **«Se muestra»** (o substring equivalente) en `CalculatorResults` — pasa con cualquier
valor numérico previo si el árbol no está stale (falso positivo potencial). Los tres inversos
reportaron **0** correctamente en este turno, pero el contrato substring no distingue
«Se muestra 63» (huérfano) de «Se muestra 0».

**Gap tool complementario a stale probe:** `run_post_act_verify` en `action_timing.py` solo
hace `needle.lower() in name.lower()` — no extrae ni compara valor numérico. La lógica
`_extract_numeric` existe en `tests/integration/calculator_harness.py` pero **no** está
expuesta al agente vía MCP.

**Refuerza / extiende solución propuesta:**
- [ ] Parámetro `verify_expected_value` en `invoke_element` / `click_element` (opcional):
      leer `CalculatorResults` vía spy, `_extract_numeric(name)`, comparar con expected
      (tolerancia locale coma/punto).
- [ ] Rechazar verify si needle es solo prefijo locale (`muestra`, `display is`) sin dígitos.
- [ ] Respuesta verify incluir `{raw_name, parsed_value, expected, match}` para diagnóstico.

**Performance:** re-probe flyout tras stale post-equal marcó **⚠ SLOW** (`find_ms`+`verify_ms`
≥3000 ms) — acoplado a re-find sin `fresh=true` tras invalidación parcial; ver `120902`.

## Evidencia adicional — turno gate reassess (2026-09-05 21:10)

**Verify target equivocado (no stale):** gate Standard `3+4=7` — `spy_inspect(CalculatorResults)`
«Se muestra 7» ✓ pero `invoke_element(equalButton, verify_name_contains=…)` falló verify porque
`_finish_action_with_verify` leyó el **nombre de equalButton**, no el display. Propuesta dedicada:
`20260905_211200_post-act-verify-display-target.md`.

**Refuerza `verify_expected_value`:** hasta aplicar fix de target, el agente debe pasar
`verify_automation_id=CalculatorResults`; con fix aplicado, añadir comparación numérica
(`expected=7`) en lugar de substring «Se muestra».

# post-act verify: apuntar CalculatorResults, no al botón actuado

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | aplicada |
| **Fecha** | 2026-09-05 21:12:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | tools/ui_automation.py, tools/action_timing.py |
| **Tool afectada** | invoke_element, click_element |
| **Tipo de gap** | tool_gap |
| **Nivel** | L4 |
| **Impacto** | alto |
| **MCP versión** | v0.2.1 (up to date) |

## Resumen

**Problema:** En gate `calculator_perfect_reassess`, `invoke_element(equalButton, verify_name_contains="7")`
devolvió **verify failed** aunque `spy_inspect(CalculatorResults)` confirmó **«Se muestra 7»** inmediatamente
después. `_finish_action_with_verify` usa como target de verificación el `automation_id` del elemento
actuado (`equalButton`) cuando no se pasa `verify_automation_id` — el nombre del botón «=» no contiene
«7». El agente interpretó un gap MCP de display; en realidad el contrato verify apunta al control
equivocado.

**Solución:**

1. Parámetro explícito `verify_automation_id` documentado como **obligatorio** cuando
   `verify_name_contains` refiere al display (Calculadora: `CalculatorResults`).
2. Heurística opcional en `_finish_action_with_verify`: si `verify_name_contains` está set y el
   `automation_id` actuado termina en `Button` / es operador teclado (`equalButton`, `plusButton`, …)
   y existe `CalculatorResults` en árbol → verificar **display**, no botón.
3. Respuesta verify fallida incluir `verify_target_used`, `actual_name`, `hint`:
   `"pass verify_automation_id='CalculatorResults' for display checks"`.
4. (Complemento) Parámetro `verify_expected_value: float | str | null` — parsear numérico del
   `name` UIA (`_extract_numeric`) en lugar de substring ciego; ver consolidación con
   `20260905_130200_scientific-display-verify-stale-read.md`.

**Dónde:** `ui_automation.py` (`_finish_action_with_verify`, `do_invoke_element`, `do_click_element`),
`action_timing.py` (`run_post_act_verify`), `docs/MCP_TOOLS_REFERENCE.md`.

## Contexto del turno

Turno `calculator_perfect_gate_reassess` (MCP v0.2.1):

- `reuse calc`; Standard; `clear→3+4=equal` InvokePattern **1190 ms**.
- `spy_inspect(CalculatorResults)` → **«Se muestra 7»** ✓; screenshot `awdui_1788653503304_45.png`.
- `invoke_element` con `verify_name_contains` sobre `equalButton` → **✗ verify failed** (gap routing).
- `spy_tree` Standard **252 nodos**, `max_depth=12`; gate spy_tree **1/9 modos**.
- Skills: `awdui-mcp-objective`, `calculator-mcp-harness`.

## Cambio propuesto (pseudodiff)

```python
# ui_automation.py
_CALC_DISPLAY_AIDS = frozenset({"CalculatorResults", "CalculatorExpression", "Header"})
_CALC_KEYPAD_SUFFIX = ("Button",)  # equalButton, num3Button, plusButton, ...

def _resolve_verify_target(
    acted_aid: str | None,
    verify_automation_id: str | None,
    verify_name_contains: str | None,
    window_title: str | None,
) -> str | None:
    explicit = (verify_automation_id or "").strip()
    if explicit:
        return explicit
    needle = (verify_name_contains or "").strip()
    if not needle or not acted_aid:
        return acted_aid
    # Display substring on keypad action → verify CalculatorResults
    if acted_aid.endswith("Button") and acted_aid not in _CALC_DISPLAY_AIDS:
        from tools.spy_bridge import spy_verify_live
        if spy_verify_live("CalculatorResults", window_title, require_enabled=False).get("live"):
            return "CalculatorResults"
    return acted_aid

def _finish_action_with_verify(...):
    verify_target = _resolve_verify_target(
        result.get("element", {}).get("automation_id") or automation_id,
        verify_automation_id,
        verify_name_contains,
        window_title,
    )
    v = run_post_act_verify(
        window_title=window_title,
        verify_automation_id=verify_target,
        verify_name_contains=needle or None,
    )
    if v.get("verified") is False:
        v["verify_target_used"] = verify_target
        v.setdefault("hint", "use verify_automation_id='CalculatorResults' for display")
```

```python
# action_timing.py — optional numeric verify
def run_post_act_verify(..., verify_expected_value: Optional[str] = None):
    ...
    if verify_expected_value is not None:
        parsed = _extract_numeric(name)
        expected = _extract_numeric(str(verify_expected_value))
        if parsed != expected:
            return {"verified": False, "verify_error": "numeric mismatch", ...}
```

## Verificación de duplicados

- **Consolidar con** `20260905_130200_scientific-display-verify-stale-read.md` (stale read +
  `verify_expected_value` numérico). Esta propuesta cubre el **target equivocado** (equalButton vs
  CalculatorResults) — root cause distinto del stale PID.
- **Distinto** de `20260905_120902` (invalidación cache post-launch).
- Sin propuesta previa sobre default verify target en `_finish_action_with_verify`.

## Test de abstracción

Cualquier app con botón de acción + campo resultado separado (editores, conversores, formularios
con label de salida) se beneficia de `verify_automation_id` explícito o heurística display-target —
no síntoma Calculadora puntual.

## Criterio de aceptación

- [ ] `tests/test_post_act_verify_target.py`: mock equalButton act + verify_name_contains «7» →
      spy llamado con `automation_id=CalculatorResults`, no `equalButton`.
- [ ] `tests/test_post_act_verify_target.py`: verify explícito `verify_automation_id=Foo` no
      sobreescrito por heurística.
- [ ] Live Calculadora: `invoke_element(equalButton, verify_name_contains="7")` tras `3+4=` →
      `verified=true`, `verify_name` contiene «7».
- [ ] Respuesta fallida incluye `verify_target_used` + `hint`.
- [ ] `MCP_TOOLS_REFERENCE.md` § `invoke_element` / `click_element`: documentar
      `verify_automation_id` para checks de display.

## Beneficios futuros

- Gate `calculator_perfect` deja de bloquearse por falso negativo verify en `equalButton`.
- Agente recibe contrato claro: actuar botón, verificar display por `automation_id` separado.
- Base para `verify_expected_value` numérico sin substring «Se muestra» genérico.

## Esfuerzo observado

- Operación aritmética OK en **~500 ms** por tecla; equal **1190 ms** (SLOW).
- Verify fallido obligó a `spy_inspect` manual — paso extra ~200–400 ms redundante.

## Evidencia adicional — turno `calculator_perfect_spy_tree_gate_complete` (2026-09-05 21:20)

- `calculator_perfect=true`, `objective_met=true` declarados con workaround documentado.
- Gate G1 (spy_tree ×9 modos depth 12) y G3 (About legal links UIA) **cerrados** en este turno.
- Gap **persiste sin fix MCP**: `invoke_element(equalButton, verify_name_contains=…)` sigue
  apuntando verify al botón actuado; `spy_inspect(CalculatorResults)` confirma display OK.
- `state.json` → `calculator_perfect_gaps[0]` y `last_cycle.next` lo listan como único fix
  MCP opcional post-objetivo; **prioridad alta** para cerrar contrato verify atómico en
  `invoke_element` / `click_element` sin `verify_automation_id` explícito.

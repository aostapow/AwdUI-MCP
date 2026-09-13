# NavView ListItem: verify_name_contains → Header + short-circuit idempotente

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-07 23:20:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | `tools/ui_automation.py`, `tools/action_timing.py` |
| **Tool afectada** | `invoke_element`, `click_element` (post-act verify) |
| **Tipo de gap** | deteccion |
| **Nivel** | L4 |
| **Impacto** | medio |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** En Calculadora UWP (F-05), `invoke_element(Standard, verify_name_contains="Estándar")`
consumió **8836 ms** y falló verify aunque el modo ya estaba activo (`Header` ya «Estándar»).
Con `verify_name_contains` seteado, `_finish_action_with_verify` usa `run_post_act_verify` sobre el
**acted** `automation_id` (`Standard` ListItem), no `Header`. Re-seleccionar el modo actual no
cambia el nombre del ListItem ni `SelectionItem.is_selected`; el poll agota timeout. Verify manual
(`Header` + `num7Button`) resolvió en **47 ms**.

**Solución:**

1. En `_resolve_verify_target`: si `acted_role` es `ListItem`/`TreeItem` de NavView y existe
   `Header` live en árbol → redirigir verify a `automation_id=Header` (paridad con fix aceptado
   `CalculatorResults` para teclado — `211200`).
2. En `_finish_action_with_verify` / `run_selection_item_verify`: si `pre_header_name` ya contiene
   el `needle` (normalizado, sin acentos opcional) → retornar `verified=true`,
   `verify_method=Header.already_active`, `verify_ms` < 50 ms (sin poll).
3. Si verify en Header falla pero `SelectionItem.is_selected` en acted aid es true y needle ⊆
   `acted_name` → `verify_method=SelectionItem.already_selected`.
4. Respuesta incluir `verify_target_used` siempre que haya redirect.

**Dónde:** `ui_automation.py` (`_resolve_verify_target`, `_finish_action_with_verify`),
`action_timing.py` (helper `_header_contains_needle`); tests `tests/test_navview_verify_routing.py`;
`docs/MCP_TOOLS_REFERENCE.md` § `invoke_element` verify.

## Contexto del turno

| Paso | Resultado | Timing |
|------|-----------|--------|
| F-05 observe | Header ya «Estándar»; NavView cerrado | — |
| `invoke_element` TogglePaneButton | OK verify «Cerrar» | 414 ms |
| `list_elements` NavView | 8 ListItem incl. `Standard` | 1195 ms |
| `invoke_element` Standard + `verify_name_contains` | verify **FAIL** | **9096 ms SLOW** |
| Verify manual Header + `num7Button` | OK | 47 ms |
| `list_elements` teclado | 31 Button | 2782 ms |
| Flujo F-05 | **met** con fricción documentada | 13539 ms total |

Skills: `awdui-mcp-automejora`, `action-narration`. Run: `calculadora-2026-09-07`.

## Cambio propuesto (pseudodiff)

```python
# ui_automation.py

_NAV_MODE_HEADER_AIDS = frozenset({"Header"})  # generic: any app with Header + Nav ListItem

def _resolve_verify_target(..., acted_role: Optional[str] = None) -> Optional[str]:
    ...
    if needle and aid and (acted_role or "").lower() in ("listitem", "treeitem"):
        header_live = spy_verify_live(automation_id="Header", window_title=window_title, ...)
        if header_live.get("live"):
            return "Header"
    return aid

# _finish_action_with_verify — before run_post_act_verify:
pre_header = result.get("pre_header_name") or ""
if needle and _header_contains_needle(pre_header, needle):
    result["verified"] = True
    result["verify_method"] = "Header.already_active"
    result["verify_ms"] = timer.elapsed_since_verify_start()
    return timer.attach(result)
```

```python
# action_timing.py
def _header_contains_needle(header_name: str, needle: str) -> bool:
    return _norm_text(needle) in _norm_text(header_name)
```

## Verificación de duplicados

- **Complementa** `aceptadas/20260905_211200_post-act-verify-display-target.md` (teclado →
  `CalculatorResults`) — este gap es **NavView mode** → `Header`.
- **Complementa** `20260906_212500_selection-item-verify-fast-poll-phase.md` (presupuesto poll
  Teams/Electron) — no cubre routing cuando `verify_name_contains` está seteado ni re-select
  idempotente.
- **No duplica** `20260905_210300` (DataItem Calendar click) — distinto control/pattern.
- **Evidencia** en `runs/calculadora-2026-09-07/improvements.jsonl` línea friction F-05.

## Test de abstracción (L4)

Cualquier app WinUI/UWP con NavigationView + `Header` (Settings, Mail, Calculadora modos)
beneficia: verify de cambio de modo por substring en Header, no en ListItem offscreen/stale.

## Esfuerzo observado

- 8,8 s de poll fallido + re-verify manual del agente.
- Flujo `met` pero `invoke_element` outcome `partial` en `mcp-usage.jsonl`.
- `list_elements` 2782 ms — dentro de backlog performance existente; **no** objeto de esta propuesta.

## Criterio de aceptación

- [ ] Live Calculadora F-05 con Header ya «Estándar»: `invoke_element(Standard,
      verify_name_contains="Estándar")` → `verified=true`, `verify_method=Header.already_active`,
      `verify_ms` < 100 ms.
- [ ] Live cambio Estándar → Científica: verify en `Header` contiene «Científica» < 1500 ms p95.
- [ ] `tests/test_navview_verify_routing.py`: mock pre_header con needle → no poll;
      mock ListItem act + Header live → `verify_target_used=Header`.
- [ ] `MCP_TOOLS_REFERENCE.md` § verify: documentar `Header.already_active` y redirect NavView.
- [ ] Regresión Teams TreeItem: no degradar `verify_name_contains` en chat (distinto path).

## Beneficios futuros

- Menos falsos negativos y re-intentos en lab Calculadora (F-05..F-12).
- Patrón reutilizable WinUI NavView sin hardcodear `if calculator`.
- Complementa gate `calculator_perfect` / harness sin workaround verify duplicado.

# spy_invoke UWP: role ListItem hardcodeado → verify SelectionItem erróneo

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-07 23:22:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | `tools/ui_automation.py` |
| **Tool afectada** | `invoke_element` |
| **Tipo de gap** | deteccion |
| **Nivel** | L4 |
| **Impacto** | alto |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** En apps UWP/WinUI, el fast-path `spy_invoke_element` construye el elemento
resultante con `"role": "ListItem"` **hardcodeado** aunque el control actuado sea `Button`
(p. ej. `ClearHistory`, `MemoryButton`, `HistoryButton`). Eso activa
`use_selection_verify` en `_finish_action_with_verify` y ejecuta
`run_selection_item_verify`, que espera cambio de `Header` o `SelectionItem.is_selected`.
Acciones que mutan sub-árbol (borrar historial, limpiar memoria) no cambian header ni
selección → verify falla tras poll completo (**~10 s** total en F-13) aunque el act fue OK
(screenshot confirma historial vacío).

**Solución:**

1. Propagar `role`, `name` y `control_type` reales desde la respuesta de
   `spy_invoke_element` / `spy_inspect_element` — nunca hardcodear `ListItem`.
2. Restringir `use_selection_verify` a roles reales
   `ListItem|TreeItem|TabItem|DataItem` **y** método con `SelectionItem` o invoke sobre
   item de lista (no todo `InvokePattern`).
3. Para `Button`/`Hyperlink` sin `verify_*` explícitos: omitir verify post-act
   (`verified: null`) o usar verify por defecto `do_wait_for_element` solo si el control
   debe seguir existiendo.
4. Opcional: parámetro `verify_children_absent` (automation_id contenedor + role hijo)
   para acciones destructivas — ver propuesta complementaria `232201`.

**Dónde:** `do_invoke_element` (~L702–740), `_finish_action_with_verify`; tests
`tests/test_spy_invoke_element_role.py`; `docs/MCP_TOOLS_REFERENCE.md` § verify routing.

## Contexto del turno

| Paso | Resultado | Timing |
|------|-----------|--------|
| F-13 prep | `invoke_element` HistoryButton abre flyout | 425 ms |
| observe | `ClearHistory` + ListItem `2 + 2= 4` en flyout | — |
| `invoke_element` ClearHistory | act OK; verify **FAIL** SelectionItem | **10555 ms SLOW** |
| verify manual | `list_elements` cache stale ListItem | 0 ms (cache hit) |
| recovery | `invalidate_cache` → ListItem vacío; screenshot OK | — |

Run: `calculadora-2026-09-07`. Flow F-13 **met** con workaround manual.
Skills: `awdui-mcp-automejora`, `action-narration`.

## Cambio propuesto (pseudodiff)

```python
# ui_automation.py — do_invoke_element UWP spy path (≈L718–727)

spy = spy_invoke_element(name=name, automation_id=automation_id, window_title=window_title)
if spy.get("success"):
    elem = spy.get("element") or {}
    spy["element"] = {
        "automation_id": automation_id or elem.get("automation_id") or "",
        "name": name or elem.get("name") or "",
        "role": (elem.get("role") or elem.get("control_type") or "Control"),
    }
    # ... _finish_action_with_verify
```

```python
# _finish_action_with_verify — tighten selection verify gate

elem_role = (elem.get("role") or "").strip().lower()
selection_roles = frozenset({"treeitem", "listitem", "tabitem", "dataitem"})
use_selection_verify = (
    not explicit_verify_aid
    and not needle
    and verify_target == acted
    and elem_role in selection_roles
    and ("SelectionItem" in method or selection_like_invoke)
)
```

## Verificación de duplicados

| Archivo | Relación |
|---------|----------|
| `232000_navview-listitem-verify-header-idempotent` | **Complemento** — idempotencia NavView cuando verify sí aplica a ListItem |
| `212500_selection-item-verify-fast-poll-phase` | Perf del poll — no corrige routing erróneo |
| `234601_invoke-element-successor-automation-id` | Swap id post-toggle — distinto concern |

## Test de abstracción

Cualquier app Store/UWP donde `spy_invoke_element` actúa `Button`, `ToggleButton` o
`Hyperlink` sin verify explícito — no solo Calculadora.

## Criterio de aceptación

- [ ] `tests/test_spy_invoke_element_role.py`: mock spy retorna `role=Button` →
      `_finish_action_with_verify` **no** llama `run_selection_item_verify`.
- [ ] F-13 replay: `invoke_element(ClearHistory)` verify_ms < 500 ms o `verified: null`
      sin FAIL; screenshot/historial vacío OK.
- [ ] Regresión NavView ListItem (`Standard`) sigue usando selection/header verify.
- [ ] Documentar en `MCP_TOOLS_REFERENCE.md` que verify default depende del rol real.

## Beneficios futuros

- Elimina ~8–10 s de poll inútil en botones UWP vía spy path.
- Reduce falsos `partial` en lab flows y matriz de validación.
- Verify post-act alineado con semántica del control (no todo invoke = selección).

## Esfuerzo observado

- 1 invoke con verify fail **10.5 s** + 2 tools recovery (`invalidate_cache`, re-list).
- Agente debió inferir verify incorrecto y escalar a invalidate manual.

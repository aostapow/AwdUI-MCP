# invoke_element exitoso: invalidar cache list_elements post-mutación

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-07 23:22:01 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | `tools/ui_automation.py`, `detection/orchestrator.py` |
| **Tool afectada** | `invoke_element`, `click_element`, `list_elements` |
| **Tipo de gap** | deteccion |
| **Nivel** | L4 |
| **Impacto** | alto |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** Tras `invoke_element(ClearHistory)` exitoso (historial realmente vacío —
screenshot «No hay historial»), `list_elements` devolvió el ListItem obsoleto `2 + 2= 4`
desde `_tree_cache` (TTL ~5 s, hit **0 ms**) hasta que el agente invocó
`invalidate_cache` manualmente. `expand_element` y `set_element_value` ya invalidan
`invalidate_tree_cache(window_title)` en éxito; **`invoke_element` / `click_element` no**.

**Solución:**

1. Tras `success=true` en `do_invoke_element`, `do_click_element`, `act_on_control`
   (Invoke/Click), llamar `invalidate_tree_cache(window_title)` — paridad con
   `do_expand_element`.
2. En `_finish_action_with_verify`, si verify confirma mutación estructural
   (`verified=true` y `verify_method` indica cambio) → invalidar también.
3. Respuesta enriquecida opcional: `cache_invalidated: true`, `cache_keys_cleared: N`.
4. Documentar que agentes **no** deben depender de `invalidate_cache` manual tras cada
   act mutante (mantener tool para recovery PID/huérfano — ver `120902`).

**Dónde:** `_finish_action_with_verify` o helper `_invalidate_after_mutating_act`;
`docs/MCP_TOOLS_REFERENCE.md` § `list_elements` / `invalidate_cache`.

## Contexto del turno

- F-13 Calculadora: ClearHistory OK en UI; `list_elements` post-act → ListItem stale.
- `improvements.jsonl`: gap P1 «invalidate subtree cache en invoke verify success o
  post-act on HistoryFlyout».
- Recovery: `invalidate_cache` → re-list vacío → screenshot verify **met**.
- MCP v0.4.0; usuario `ariel.ostapow`.

## Cambio propuesto (pseudodiff)

```python
# ui_automation.py

def _invalidate_list_cache_after_act(
    result: dict,
    window_title: Optional[str],
) -> None:
    if not result.get("success"):
        return
    try:
        from detection.orchestrator import invalidate_tree_cache
        n = invalidate_tree_cache(window_title)
        result["cache_invalidated"] = True
        result["cache_keys_cleared"] = n
    except Exception:
        pass

# Al final de _finish_action_with_verify, antes de return:
_invalidate_list_cache_after_act(result, window_title)
return timer.attach(result)
```

```python
# orchestrator.py — opcional: clave cache incluye ancestor_automation_id
# Tras ClearHistory invalidar también entradas con ancestor=HistoryFlyout
```

## Verificación de duplicados

| Archivo | Relación |
|---------|----------|
| `120902_stale-element-cache-invalidate` | **Consolidar evidencia** — cubre PID/relaunch; este ítem cierra gap post-act invoke |
| `232200_spy-invoke-uwp-hardcoded-listitem-wrong-verify` | Verify fail distinto; ambos requeridos para F-13 sin workaround |
| `211200_post-act-verify-display-target` | Display verify — no sustituye cache list |

## Test de abstracción

Cualquier act mutante UWP/WinForms (clear, delete row, dismiss flyout item) donde hijos
desaparecen del árbol — Calculadora historial/memoria, grids, listas.

## Criterio de aceptación

- [ ] `tests/test_uia_tree_cache.py`: invoke mock success → siguiente `list_elements`
      cache miss (elementos actualizados).
- [ ] F-13 replay: tras ClearHistory, **sin** `invalidate_cache` manual, `list_elements`
      no devuelve ListItem previo (< 500 ms).
- [ ] Regresión perf: warm cache sigue válido si invoke falla (`success=false`).
- [ ] `MCP_TOOLS_REFERENCE.md`: nota «mutating invoke auto-invalidates list cache».

## Beneficios futuros

- Elimina paso obligatorio `invalidate_cache` tras cada act que cambia sub-árbol.
- Verify de flujos lab (F-13, F-14, memoria) confiable en una sola tool post-act.
- Alineación con `expand_element` / `set_element_value` ya implementados.

## Esfuerzo observado

- 2 tools extra de recovery por flujo (invalidate + re-list).
- Riesgo de falso OK si agente confía en list cache sin screenshot.

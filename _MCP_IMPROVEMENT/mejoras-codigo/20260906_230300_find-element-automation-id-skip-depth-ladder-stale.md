# find_element: omitir depth-ladder si automation_id no resuelve (stale/cold 4s)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-06 23:03:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | `detection/backends/uia_backend.py`, `tools/ui_automation.py`, `detection/orchestrator.py`, `tools/target_window.py` |
| **Tool afectada** | `find_element`, `wait_for_element`, `element_exists` |
| **Tipo de gap** | performance |
| **Nivel** | L4 |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** Tras el fix turno 11 (`comtypes` `FindFirst` por `AutomationId`, orchestrator
UIA-first, skip spy con `automation_id`), `do_find_element` local baja a **314 ms** (antes ~4 s).
En MCP vivo con **proceso Calculadora stale/huérfano**, el cold path sigue en **4013 ms**
(warm **557 ms**). Cuando `FindFirst` + `child_window` no encuentran el id en el HWND
resuelto, `UIABackend.find_elements` cae al **depth ladder** (`4→8→14` × `list_elements`),
reproduciendo el costo previo aunque el agente pasó `automation_id` explícito.

**Solución:** (1) Si `automation_id` está seteado y la búsqueda dirigida
(`_find_raw_by_automation_id_comtypes` → `child_window` → descendants cap 16) falla,
**no** ejecutar depth-ladder; retornar `found: false` con `find_path: "automation_id_miss"`
y `duration_ms` acotado (<800 ms objetivo). (2) Antes del miss final, comparar PID/HWND del
target con `list_windows` / sesión (`resolve_window_handle`); si mismatch o proceso muerto →
`code: stale_instance`, `hint: launch_app(replace=true) + set_target_window`, invalidar
`_tree_cache` (complementa `120902`). (3) Exponer `find_path` y `backend_used` en respuesta
MCP para auditoría eficiencia (`tool_validation` / `objective_met`).

**Dónde:** `uia_backend.find_elements` (rama post-`_find_raw_by_automation_id`),
`do_find_element`, tests `tests/test_uia_find_performance.py`.

## Contexto del turno

- **Turno 11:** fix aplicado en `uia_backend` + `orchestrator` (UIA antes FlaUI para
  `automation_id`); pytest **32 passed**.
- **Local:** `do_find_element(automation_id=num7Button)` **314 ms**.
- **MCP live:** cold **4013 ms** con proceso stale; warm **557 ms** tras reconexión parcial.
- **Entorno:** `restart-awdui-mcp.ps1 -KillOrphans` desconectó MCP — toggle manual Settings.
- **Estado:** `objective_met: false`, eficiencia **partial** (auditoría 87 tools).
- Skills: `awdui-mcp-objective`, `calculator-mcp-harness`, `mcp-improvement-cycle`.

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| Cold 4013 ms tras miss dirigido | performance | L4 | Sí (este archivo) |
| Proceso stale sin señal en find | entorno | L4 | Incluido (PID check + hint) |
| Fix comtypes 314 ms local | — | — | **Aplicado turno 11 — no re-proponer** |
| KillOrphans → MCP disconnect | entorno | L3 | Documentar en `awdui-mcp-restart.mdc` (ejecución) |
| Match cross-HWND id=4101 | deteccion | L4 | Backlog `180000` (ortogonal) |

No es `ejecucion`: el fast path existe; el fallback ladder es comportamiento de código residual.

## Cambio propuesto (pseudodiff)

```python
# uia_backend.py — UIABackend.find_elements
if window and automation_id:
    raw = _find_raw_by_automation_id(window, automation_id)
    if raw:
        d = _pywinauto_to_element(raw)
        if d and _matches(...):
            return [d]
    # NEW: targeted miss — do not depth-ladder
    stale = _target_window_stale_hint(window_title, window_handle)
    if stale:
        return []  # orchestrator surfaces stale dict via do_find_element wrapper
    return []  # fast miss; find_path logged

# Remove or guard:
# depth_ladder = _FIND_DEPTH_LADDER_AUTOMATION_ID if automation_id else ...
# for depth in depth_ladder: ... list_elements ...  # only when automation_id is None
```

```python
# ui_automation.py — do_find_element result
return {
    "found": False,
    "find_path": "automation_id_miss",  # or comtypes_hit | child_window | depth_ladder (legacy name only)
    "hint": stale.get("hint") if stale else None,
    ...
}
```

## Test de abstracción (L4)

Cualquier app WinForms/UWP/Electron con `automation_id` estable: miss dirigido no debe
disparar barrido `list_elements` multi-segundo. Beneficia auditoría 87 tools y harness
Calculadora/Teams sin IDs de producto en servidor.

## Verificación de duplicados

| Slug backlog | Acción |
|--------------|--------|
| `120902_stale-element-cache-invalidate` | **Complementar** — este ítem cubre fast-fail find + hint; 120902 cubre invalidate global |
| `180000_find-element-target-scope-false-positive` | **Relacionado** — scope evita match erróneo; este ítem evita ladder lento en miss |
| `214800_invoke-element-probe-timing` | **Parcial** — skip stale spy en invoke; extender patrón a find miss UWP |
| Fix turno 11 comtypes | **No duplicar** — asumir aplicado |

**Acción mantenedor:** tras validar live cold <800 ms en miss stale, archivar tema
`find-element-perf-automation-id` junto con evidencia turno 11.

## Esfuerzo observado

- Diagnóstico + implementación comtypes/UIA-first: turno 11 (~1 h agentico).
- Validación live bloqueada por MCP disconnect post-KillOrphans.
- Gap residual: 4013 ms cold vs 314 ms local — ratio ~13× atribuible a depth-ladder fallback.

## Criterio de aceptación

- [ ] `tests/test_uia_find_performance.py`: mock miss comtypes → **no** llama `list_elements` en ladder.
- [ ] Mock stale PID → respuesta incluye `code=stale_instance` o `hint` launch_app sin >1 s wall.
- [ ] Live Calculadora fresh: `find_element(automation_id=num7Button)` p95 < **800 ms** (warm y cold).
- [ ] Live con calc huérfana: miss < **800 ms** + hint, no 4 s ladder.
- [ ] `find_path` presente en JSON MCP; `docs/MCP_TOOLS_REFERENCE.md` § `find_element`.
- [ ] Auditoría eficiencia: fila `find_element` deja WARN slow solo si `find_path=depth_ladder` (no debería ocurrir con automation_id).

## Beneficios futuros

- Cierra brecha local vs MCP en auditoría `objective_met` / eficiencia.
- Agente recibe señal `stale_instance` en find (no solo invoke) → menos reintentos ciegos.
- Depth ladder queda reservado a búsquedas por `name`/`role` sin id estable.

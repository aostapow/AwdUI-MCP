# find_element: tope wall-clock en búsqueda por name/role sin automation_id

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 19:51:26 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | `detection/backends/uia_backend.py`, `tools/ui_automation.py` |
| **Tool afectada** | `find_element`, `wait_for_element`, `element_exists` |
| **Tipo de gap** | performance |
| **Nivel** | L4 |
| **Versión MCP** | 0.4.0 |

## Resumen

**Problema:** `find_element(name="Borrar historial", …)` en flyout de Explorador devuelve NOT FOUND tras
**~36 s** (`find_neg`), porque el depth ladder `(6,10,14,18,24)` repite `list_elements` completos por
cada escalón cuando no hay `automation_id` (solo aplica skip ladder la propuesta `230300` para id).

**Solución:** (1) Tras primer pase raw/direct sin match, no ejecutar ladder completo si `name`/`role`
sin `automation_id` — retornar vacío con `find_path=negative_fast` y `elapsed_ms` < **3 s** default.
(2) Parámetro opcional `find_budget_ms` (default 8000) para búsquedas con ladder parcial.
(3) Header JSON: `depth_steps_attempted`, `find_path`.

**Dónde:** `uia_backend.find_elements`, `do_find_element`; tests `tests/test_uia_find_performance.py`.

## Contexto del turno

- Lab `escritorio-windows-2026-09-10`, `discover_flows` subárbol **F-08** (flyout Ubicaciones recientes).
- Ya visible 1 `MenuItem` útil (carpeta lab); agente buscó chrome opcional «Borrar historial».
- Evidence: `find_neg` **36354 ms**; `list_elements` Button **10583 ms** en mismo turno.

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| find_element 36s NOT FOUND | performance | L4 | Sí (este archivo) |
| Probe footer flyout innecesario | routing_tool | L3 | Skill complementaria `discover-subtree-flyout-scan` |

No es `ejecucion` pura: aunque el agente no debía buscar «Borrar historial», el MCP no debe quemar 36s en miss.

## Cambio propuesto

```python
# uia_backend.py — find_elements (sin automation_id)
if not automation_id and (name or role):
    direct = self._find_raw_direct(...)
    if not direct:
        return []  # find_path=negative_fast; skip _FIND_DEPTH_LADDER
    # ladder solo si direct parcial o fuzzy
```

```python
# ui_automation.py — do_find_element
out["find_path"] = "negative_fast" | "depth_ladder" | "automation_id_direct"
```

Documentar en `MCP_TOOLS_REFERENCE.md` § `find_element`: miss por name debe ser rápido; usar `list_elements(role=…)` para inventario.

## Test de abstracción (L4)

Cualquier WinForms/UWP/Explorer con flyout: miss por texto parcial no debe bloquear discover 30+ s.

## Verificación de duplicados

| Propuesta | Relación |
|-----------|----------|
| `20260906_230300_find-element-automation-id-skip-depth-ladder-stale` | Complemento — solo automation_id hoy |
| `20260906_180100_discovery-tools-wall-clock` | Distinto módulo (discover_target) |

## Esfuerzo observado

Turno discover F-08: >45 s en tools de búsqueda negativa; `objective_met` sigue false por latencia acumulada.

## Criterio de aceptación

- [ ] `find_element(name=…)` miss p95 < **3 s** en Explorer flyout (test integration o mock ladder).
- [ ] `find_path=negative_fast` en JSON cuando no hay automation_id y raw vacío.
- [ ] `tests/test_uia_find_performance.py` cubre name-only miss.
- [ ] `docs/MCP_TOOLS_REFERENCE.md` actualizado.

## Beneficios futuros

Discover lab y producto dejan de pagar depth ladder en chrome opcional no encontrado.

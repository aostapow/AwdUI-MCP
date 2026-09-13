# invoke_element: exponer automation_id sucesor tras toggle UIA

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_tool |
| **Estado** | propuesta |
| **Fecha** | 2026-09-07 23:46:01 |
| **Usuario sesión** | ariel.ostapow |
| **Tool afectada** | `invoke_element`, `click_element`, `act_on_control` |
| **Tipo de gap** | tool_gap |
| **Nivel** | L4 |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** Tras `invoke_element(NormalAlwaysOnTopButton)` exitoso (pin, **198 ms**), el
control desaparece del árbol UIA y reaparece como `ExitAlwaysOnTopButton` (`Volver a vista
completa`). El agente re-busca el id anterior → `find_element` **8705 ms SLOW** +
`NOT FOUND`. El flujo F-24 fue `met` vía `spy_inspect` manual, pero no hay señal MCP del
cambio de identidad.

**Solución:** Tras invoke/click verificado OK, si el `automation_id` actuado ya no resuelve
en ≤300 ms, ejecutar lectura live acotada (misma región bbox ± margen, mismo `role=Button`,
mismo `window_title`) y devolver en la respuesta:

- `automation_id_after` — id del control sucesor
- `control_identity_changed: true`
- `hint` — «post-toggle id changed; use automation_id_after for unpin»

Heurística **genérica** (sin listas por app): mismo rol + bbox overlap >50% + distinto
`automation_id` + InvokePattern disponible. Opcional: detectar prefijos complementarios
(`Normal*` ↔ `Exit*`, `On*` ↔ `Off*`) solo como hint textual, no como filtro hardcoded
de producto.

**Dónde:** `tools/act_tools.py`, `tools/uia_pattern_tools.py` post-act verify;
`docs/MCP_TOOLS_REFERENCE.md` § `invoke_element`.

## Contexto del turno

- Lab Calculadora F-24: pin **198 ms**; `spy_inspect(NormalAlwaysOnTop)` post-pin fail;
  `find_element(NormalAlwaysOnTopButton)` **8705 ms** NOT FOUND;
  `list_elements` muestra `ExitAlwaysOnTopButton`; cleanup unpin **521 ms** OK.
- `flows.json` / `improvements.jsonl` ya documentan swap en artefactos lab — el MCP no
  lo expone al agente en tiempo de invoke.
- MCP v0.4.0.

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| Sin señal id sucesor post-invoke | tool_gap | L4 | Sí (este archivo) |
| find 8705 ms buscando id obsoleto | performance | L4 | Consolidar `230300` fast-fail miss |
| Agente no anticipó swap | ejecucion | L2 | Lab `repo_hints_note` — complemento skill |

## Spec propuesta

Campos nuevos en respuesta JSON (breaking-none, additive):

```json
{
  "success": true,
  "verified": true,
  "automation_id": "NormalAlwaysOnTopButton",
  "automation_id_after": "ExitAlwaysOnTopButton",
  "control_identity_changed": true,
  "hint": "Toggle control replaced in UIA tree; use automation_id_after for next action"
}
```

Comportamiento:

1. Tras invoke OK + verify pass (o verify omitido con `verified=true`).
2. `find_element(automation_id=original)` rápido — si miss, bbox del elemento pre-act en cache.
3. `list_elements(role=Button, max_depth=4, ancestor region=bbox±32)` o spy live scoped.
4. Elegir candidato mismo rol, mayor IoU bbox, distinto aid.
5. Si ninguno → respuesta sin campos nuevos (sin regresión).

## Verificación de duplicados

| Archivo | Relación |
|---------|----------|
| `230300_find-element-automation-id-skip-depth-ladder-stale` | **Complemento** — reduce 8705 ms en miss; no informa sucesor |
| `211200_post-act-verify-display-target` | Verify display vs botón — distinto concern |
| Lab `repo_hints` F-24 | Workaround agente — no sustituye contrato tool |

## Test de abstracción

Patrón WinUI/UWP toggle en title bar (pin, compact, theme) donde MS reemplaza nodo UIA;
aplica a otras apps Store con par Normal/Exit sin nombrar Calculadora en código servidor.

## Criterio de aceptación / tests

- [ ] Live Calculadora F-24: invoke pin retorna `automation_id_after=ExitAlwaysOnTopButton`
- [ ] invoke unpin retorna `automation_id_after=NormalAlwaysOnTopButton`
- [ ] Botón sin swap (ej. `num7Button`) no incluye `control_identity_changed`
- [ ] `pytest tests/test_invoke_successor_automation_id.py` con mocks bbox/role
- [ ] Documentado en `MCP_TOOLS_REFERENCE.md`

## Beneficios futuros

- Evita `find_element` 8 s buscando id obsoleto tras toggles
- Agente puede encadenar unpin sin `spy_inspect` manual
- Compatible con `repo_hints_set` — hint MCP primero, repo como cache opcional

## Esfuerzo observado

- Post-pin verify: **8705 ms** find fallido + **3486 ms** list parcial antes de
  `spy_inspect` exitoso — ~12 s fricción evitable con respuesta invoke enriquecida.

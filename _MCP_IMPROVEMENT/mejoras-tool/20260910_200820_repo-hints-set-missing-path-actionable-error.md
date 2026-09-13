# repo_hints_set: error accionable y opción ensure_stub

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_tool |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 20:08:20 |
| **Usuario sesión** | ariel.ostapow |
| **Tool afectada** | `repo_hints_set` |
| **Módulo código** | `mcp-servers/awdui-server/tools/repo_action.py` (`do_repo_hints_set`) |
| **Tipo de gap** | tool_gap |
| **Nivel** | L4 |
| **Versión MCP** | v0.4.0 (up to date) |

## Resumen

**Problema:** Tras fricción en discover/execute, el agente llama `repo_hints_set` con un
`repo_path` lógico (ej. `Escritorio/Explorer/Ribbon/Ayuda`) pero el objeto **no existe** en SQLite
→ `object not found` sin indicar el siguiente paso. La lección queda solo en `improvements.jsonl`
o se pierde. Patrón repetido: Calculadora discover F-03 (`HistoryButton`), Escritorio discover-F-15.

**Solución:** (1) En error `object not found`, devolver `suggested_action: repo_capture` con el mismo
`repo_path` y campos mínimos opcionales (`automation_id`, `name`) si el caller los conoce; (2) parámetro
opcional `ensure_minimal: bool` que crea stub Swf* con `identification` mínima solo para persistir
`agent_hints` (sin screenshot ni coords) cuando el agente ya resolvió el control en UIA pero no capturó.

**Dónde:** `do_repo_hints_set`, doc `MCP_TOOLS_REFERENCE.md`, `object-repository.md` (cuándo usar
`ensure_minimal` vs `repo_capture` completo).

## Contexto del turno

- Lab `escritorio-windows-2026-09-10`, **discover-F-15** (subárbol Ayuda).
- `invoke_element` Ayuda → ventana Edge; `list_elements` sin `Link` accionable en scope.
- Cierre probe **Ctrl+W** ~915 ms OK (alineado con skill propuesta `20260910_200530`).
- `repo_hints_set` **fail**: `object not found Escritorio/Explorer/Ribbon/Ayuda` — sin `repo_capture`
  previo del botón Ayuda en Explorador (`improvements.jsonl` #9).

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| hints_set sin objeto repo | tool_gap | L4 | Sí (este archivo) |
| Agente no repo_capture antes | routing_tool | L3 | Parcial — skill ya anti-patrón; tool debe guiar |
| Edge sin Link UIA | deteccion | L3 | Skill hermana `20260910_200821` |
| Ctrl+W dismiss OK | — | — | No — ejecución correcta post-F-15 execute |

## Spec propuesta

Parámetros nuevos en `repo_hints_set`:

| Parámetro | Tipo | Default | Comportamiento |
|-----------|------|---------|----------------|
| `ensure_minimal` | bool | false | Si path ausente, `upsert` stub con `obj_class` inferido o `SwfButton` + hints |
| `automation_id` | str? | null | Requerido si `ensure_minimal=true` (o `name` + `role`) |
| `name` | str? | null | Assistive id para stub |

Respuesta en fallo (sin ensure):

```json
{
  "success": false,
  "error": "object not found: Escritorio/Explorer/Ribbon/Ayuda",
  "suggested_action": "repo_capture",
  "repo_path": "Escritorio/Explorer/Ribbon/Ayuda",
  "hint": "Call repo_capture with automation_id/name from last successful find_element, or set ensure_minimal=true if UIA id is known"
}
```

## test_abstraccion

Cualquier lab/producto que documente lecciones en repo sin haber capturado el control en la misma
sesión (flyout, ribbon, historial Calculadora).

## verificacion_duplicados

- Skill `object-repository.md` ya prohíbe hints sin capture — **complementa**, no reemplaza.
- `20260910_195126` exige `repo_hints_set` tras WARN — necesita path existente o ensure.
- Calculadora `evidence.jsonl` discover F-03: mismo síntoma documentado.

## beneficios_futuros

- Menos pérdida de memoria institucional tras discover.
- Un solo paso (`ensure_minimal`) tras `find_element` OK en discover sin screenshot obligatorio.

## criterio_aceptacion_tests

- [ ] `tests/test_repo_hints_set.py`: error incluye `suggested_action`; `ensure_minimal` crea stub y persiste hints.
- [ ] `validate_tools_reference.py` verde tras actualizar sección `repo_hints_set`.
- [ ] Replay discover-F-15: tras find Ayuda OK → `repo_hints_set(..., ensure_minimal=true, automation_id=…)` success.

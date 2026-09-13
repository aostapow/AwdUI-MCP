# Repositorio de objetos — memoria institucional

> El repo SQLite (`~/.awdui-mcp/repository.db`) **no pierde** el esfuerzo de entender un control.
> Complementa `element-map.md` (corrida) y skills de producto (IDs estables).
>
> **Política:** con `set_target_window` activo, el MCP **upsert** en cada act exitoso (`find`/`click`/`invoke`/`expand`).
> Solo se excluyen ejecutables host (Cursor, Python, shells, etc.) — ver `docs/OBJECT_REPOSITORY.md`.

## Tres capas de mapa (no competir)

| Capa | Dónde | Vida útil | Rol |
|------|-------|-----------|-----|
| **Funcional** | `flows.json` | Una corrida lab | Qué hacer (entry/action) |
| **Descubrimiento** | `runs/{run}/element-map.md` | Legible humano | OBS de la corrida |
| **Persistente** | `repository.db` + `repo-snapshot.json` | Entre sesiones | Localizador + **agent_hints** |

**Regla:** control estable y reutilizable → `repo_capture` + anotar en `element-map` el `repo_path`.

## Cuándo el MCP **consume** hints (automático)

| Clave en hint | Cuándo se aplica | Efecto |
|---------------|------------------|--------|
| `verify_automation_id` | Post-acción con `verify_name_contains` | Redirige el nodo UIA de verify |
| `metodo_preferido` / `preferred_tool` | `discover_control_interaction` | Promueve la estrategia cuyo `tools[]` incluye esa tool |
| `metodo_preferido: click_element` / `avoid_invoke` | `repo_action` Click | Salta invoke → click por coordenadas |
| `metodo_preferido: invoke_element` | `repo_action` Click | Solo invoke; sin fallback a coords |
| Cualquier hint | `find_element`, `repo_find` | Adjunta `agent_hints`, `hint_parsed`, `hint_preferred_tool` en la respuesta |

`repo_hints` sigue existiendo para **listar** hints de toda la app o leer sin resolver el control.

## Cuándo **escribir** hints

| Situación | Acción |
|-----------|--------|
| Workaround estable (invoke falla, hay que clickear) | `repo_hints_set` con `metodo_preferido: click_element` |
| Verify debe mirar otro control | `verify_automation_id: <id>` |
| Precondición / nota operativa | `precondicion:` / `nota:` (informativo en respuestas; no ejecutable solo) |
| Control nuevo | `repo_capture` + hints si ya se conoce la lección |

## `agent_hints` — qué depositar

Texto libre, líneas `clave: valor`, o JSON. El servidor parsea claves conocidas (ej. `verify_automation_id`).

| Tipo | Ejemplo |
|------|---------|
| Verify | `verify_automation_id: CalculatorResults` |
| Workaround | `nota: invoke falla; usar click_element en bbox UIA` |
| Precondición UI | `precondicion: menú Formato abierto (F-02 met)` |
| Teclado/foco | `workaround: click editor antes de send_keys` |
| Latencia | `latencia: list_elements >3s — usar automation_id directo` |
| Corrida | `ultima_corrida: teams-2026-09-07 — scroll keyboard antes de coords` |

## Tools MCP

| Tool | Rol |
|------|-----|
| `repo_capture` | Persistir control (+ `agent_hints` opcional al capturar) |
| `repo_hints_set` | **Escribir** hints (`append=true` para agregar línea) |
| `repo_hints` | **Leer** hints antes de actuar |
| `repo_find` / `repo_action` | Resolver y actuar por path lógico |
| `repo_list` | Inventario de la app |

## Protocolo por turno

1. **Tras fricción** (FAIL, workaround, verify extra): `repo_hints_set(..., append=true)` con claves estructuradas.
2. **Control nuevo estable**: `repo_capture` + línea en `element-map.md` con el mismo `repo_path`.
3. **Cierre lab** (hook incremental): `repo-snapshot.json` en la corrida.

Al **resolver** el control (`find_element`, `repo_find`, `discover_control_interaction`, `repo_action`), el servidor **lee** hints sin llamada extra.

## Puente `flows.json`

Campos opcionales en un flujo `action`:

```json
{
  "repo_path": "CargaHoras/cboHoras",
  "repo_hints_note": "select_control_item si Select del repo falla"
}
```

Si `repo_path` está seteado y el objeto no existe → `repo_capture` antes de marcar `met`.

## Puente `element-map.md`

En cada OBJ-N estable:

```markdown
### OBJ-3: Combo Horas
| repo_path | CargaHoras/cboHoras |
| hints | verify_automation_id no aplica; usar read_element post-select |
```

Tras editar el mapa, si hay `repo_path` → sincronizar hints con `repo_hints_set`.

## Formato recomendado de hints (plantilla)

```text
verify_automation_id: <id opcional>
precondicion: <estado UI requerido>
metodo_preferido: invoke_element | select_control_item | click_element
workaround: <si aplica>
nota: <libre para el próximo agente>
```

## Anti-patrones

- Aprender un workaround solo en chat — **sin** `repo_hints_set`.
- Capturar flyout/modal transitorio — repo stale.
- Duplicar en skill producto lo que ya está en repo con hints (skill = IDs estables; repo = quirks).
- `repo_hints_set` sin `repo_capture` previo — el path no existe.

## Relación con auto-repo

`maybe_remember_element` guarda tras finds exitosos **sin** hints. Completar con `repo_hints_set` cuando hay lección operativa.

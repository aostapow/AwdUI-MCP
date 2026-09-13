# Filtro de valor MCP — omitir flujos redundantes

> Parte de [awdui-mcp-automejora](../../SKILL.md). El lab existe para **mejorar el MCP**, no para recorrer toda la UI de la app.

## Principio

Al **detectar**, **encolar** o **elegir** un flujo en automejora, preguntar:

> ¿Este flujo expone un **objeto, patrón o tool** que **aún no probamos** en esta corrida (o en el corpus MCP relevante)?

Si la respuesta es **no** → el flujo **no aporta** a la automejora → **omitirlo** (no encolar, no ejecutar, o marcar `cancelled` con motivo).

Esto **no** contradice discover batch: encolar muchos candidatos en un barrido sigue siendo válido; el filtro se aplica **al analizar cada candidato** antes de append o al priorizar `execute_flow`.

---

## Qué cuenta como «nuevo» (sí ejecutar / sí encolar)

| Señal | Ejemplo |
|-------|---------|
| Rol UIA + pattern no ejercido en la corrida | primer `ComboBox` + `select_control_item`; primer `DataGrid` |
| Tool MCP o cadena de tools nueva | primera vez `expand_element`, `read_table`, `scroll_into_view` |
| Control distinto en `discovery_signals` | otro `automation_id`, otro rol, otro patrón de interacción |
| Contexto UI no probado | modal `#32770`, ventana hija, NavView, flyout, modo compacto |
| Fricción o timing nuevo | slow, verify fail, scope leak — aunque el rol ya se vio en otro flujo |
| `entry` que abre subárbol **no escaneado** | menú/modal/tab nuevo → `subtree_discovered: false` |

Un `entry` puede valer aunque el patrón «abrir menú» ya esté cubierto: el **subárbol** puede traer controles nuevos.

---

## Qué **no** aporta (omitir)

| Señal | Ejemplo |
|-------|---------|
| Mismo rol + mismo pattern + misma tool chain ya `met` | `num3Button` tras `num2Button` (ambos Button + `invoke_element`) |
| Variante funcional pura de negocio | otra operación aritmética sin control nuevo |
| Re-ejecutar affordance ya catalogada | reabrir menú cuyo `subtree_discovered: true` y hijos ya listados |
| Flujo seed del usuario sin gap técnico | «5+5» cuando suma básica ya validó Invoke + verify |

**Regla práctica:** si el único delta respecto a un flujo `met` es el **texto del botón** o el **resultado numérico**, omitir.

---

## Cómo omitir (sin romper el árbol)

1. **Discover:** no append; o append con `status: cancelled` y `notes: "skip_mcp_value: <motivo>"`.
2. **Execute:** al elegir siguiente `pending`, saltar redundantes; marcar `cancelled` antes de OBS→ACT→VERIFY.
3. **Gate `perfect`:** flujos `cancelled` por valor MCP cuentan como cerrados (como seeds cancelados con motivo); no inflar `met` artificialmente.

### Fuentes para decidir

- [repo-first-lab.md](repo-first-lab.md) — `repo_hit` sin discover cuenta como omitible si verify OK
- `flows.json` — flujos `met` y sus `discovery_signals`
- `element-map.md` / `repo-snapshot.json` — objetos ya capturados
- `mcp-usage.jsonl` / `coverage.json` — tools y roles ya usados
- [control-catalog.md](control-catalog.md) — patrón esperado por rol

---

## Excepciones (sí ejecutar aunque parezca redundante)

- **Re-VERIFY** tras fix_in_cycle en el **mismo** paso que falló (no es flujo nuevo; es validación del fix).
- **Regresión** explícita del usuario o del gate (`validate_perfect_gate`, criterio de latencia).
- **Fricción nueva** en un control «conocido» (timing, verify, scope) → ejecutar y disparar fix-in-cycle.

---

## Anti-patrones

- Ejecutar N flujos solo para subir `met / total` sin cobertura MCP nueva.
- Encolar todos los dígitos/teclas de una calculadora «por completitud funcional».
- Cancelar un `entry` que abre subárbol no descubierto solo porque «abrir menú ya lo vimos».
- Confundir **tarea de producto** (AST, carga de horas) con **vehículo lab** — en producto no aplica este filtro salvo que el turno sea automejora MCP.

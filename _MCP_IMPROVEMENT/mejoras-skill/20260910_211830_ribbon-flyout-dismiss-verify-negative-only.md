# Ribbon flyout — VERIFY dismiss sin SelectionItem poll (Inicio / Fácil acceso)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 21:18:30 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | `awdui-mcp-automejora/references/evaluacion-lab.md` + `patterns/win32-explorer-ribbon.md` |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** Tras **F-99** (`expand_element` Fácil acceso 838 ms OK), el teardown con `invoke_element` en un `ListItem` probe tardó **3738 ms** (SLOW) y **verify SelectionItem falló**, aunque el menú ya no era accionable (`element_exists` negativo suficiente).

**Solución:** Para **cerrar flyouts de cinta** (SplitButton / menús Inicio), documentar VERIFY **negativo** primero: `element_exists(name=… MenuItem clave)` NOT FOUND o `expand_element` toggle collapse en el mismo SplitButton; **no** encadenar `invoke_element` en ítem de lista solo para dismiss si el objetivo es cerrar sin elegir opción. Si se usa invoke dismiss, desactivar verify SelectionItem (`verify=false` o patrón skill «teardown no muta selección»).

**Dónde:** `evaluacion-lab.md` tabla teardown ribbon; enlace desde `20260910_210615_explorer-vista-splitbutton-flyout-teardown`.

## Análisis del gap

| Fricción | tipo_gap | Propuesta |
|----------|----------|-----------|
| dismiss invoke 3738 ms + verify fail | routing_tool | **Este archivo** (skill) |
| SelectionItem poll cost | performance | `20260906_212500_selection-item-verify-fast-poll-phase` (código) |
| Escape no cierra flyout | routing_tool | `20260910_210615` |

## Texto propuesto

### Teardown flyout cinta Inicio (Fácil acceso, Abrir, etc.)

1. **Preferir:** `expand_element` de nuevo en el **mismo** SplitButton (collapse) o click en área cinta fuera del menú (probe documentado en `210615`).
2. **VERIFY:** `element_exists` sobre un `MenuItem` distintivo del flyout → NOT FOUND; opcional `screenshot(scope=window)`.
3. **Evitar:** `invoke_element` en `ListItem` del panel lateral solo para «cerrar» — dispara verify SelectionItem innecesario (≥3 s).
4. Tras workaround: `repo_hints_set` — `nota: ribbon Inicio flyout — verify negativo, no invoke dismiss ListItem`.

## Contexto del turno

- Execute F-99 `met` WARN; `improvements.jsonl` friction dismiss_flyout.
- Expand OK; dismiss slow verify fail.

## Test de abstracción

Office-style ribbon Win32 (Explorer, algunos diálogos con menús anclados) — no atado al texto «Fácil acceso».

## Verificación duplicados

| Archivo | Acción |
|---------|--------|
| `20260910_210615_explorer-vista-splitbutton-flyout-teardown` | **Merge al implementar** — añadir fila Inicio/Fácil acceso |
| `20260906_212500_selection-item-verify-fast-poll-phase` | Complemento código — no sustituye routing |

## Criterios de aceptación

- [ ] F-99 re-ejecutable con teardown <3 s sin coords
- [ ] Distinción explícita: dismiss **Vista** SplitButton vs **Inicio** flyout en misma tabla skill
- [ ] Sin duplicar reglas de discover flyout (`195126`)

## Beneficios futuros

Menos falsos SLOW en matriz de eficiencia; agente no interpreta verify fail como flyout aún abierto cuando `element_exists` ya negó el menú.

# Explorer barra dirección — VERIFY post-flyout sin find Toolbar (F-86 patrón)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 21:25:30 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | `awdui-mcp-automejora/references/evaluacion-lab.md`, `patterns/win32-explorer-ribbon.md` (barra dirección) |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** Tras **F-86** (`invoke_element` botón «Ubicaciones anteriores» **1447 ms** OK, teardown con **Escape** y VERIFY de «ruta lab sin cambio» vía `find_element(role=Toolbar, name=<ruta completa>)` tardó **~33 s** (SLOW) aunque el flujo cumplió criterio (screenshot + probe OK).

**Solución:** Documentar VERIFY **post-cierre** de flyouts de barra de dirección (List «Dirección», no menú contextual): (1) `element_exists` negativo sobre el popup (`List` / `ListItem` del flyout); (2) **`read_element`** o **Value** del Edit/combo de dirección ya mapeado en discover — comparar texto con valor pre-act; (3) **prohibido** `find_element` por nombre de ruta completa en rol `Toolbar` (homónimos, depth ladder, miss 30+ s). Screenshot `scope=window` solo como capa final.

**Dónde:** Extender tabla execute VERIFY en `evaluacion-lab.md` (fila «Ubicaciones anteriores / recientes»); merge con `20260910_195900_explorer-breadcrumb-flyout-verify-routing`.

## Análisis del gap

| Fricción | tipo_gap | L | Propuesta |
|----------|----------|---|-----------|
| find Toolbar ruta 33 s post-Escape | routing_tool | L3 | **Este archivo** |
| Miss name-only 30+ s | performance | L4 | **Consolidar** — `20260910_195126_find-element-name-search-negative-wall-clock` (sin duplicar) |
| invoke flyout OK | — | — | No código |
| Escape cierra List Dirección | ejecucion parcial | — | Ya válido; falta doc VERIFY |

## Texto propuesto

### Flyout «Ubicaciones anteriores» / «Ubicaciones recientes» (execute)

**ACT:** `invoke_element` en `Button` de barra de dirección (patrón Invoke).

**Teardown:** `press_key` Escape (preferido) o click fuera; VERIFY negativo: `element_exists` sobre `ListItem` distintivo del flyout → NOT FOUND (<2 s).

**VERIFY «ruta sin cambio» (success_criteria lab):**

| Orden | Tool | Notas |
|-------|------|-------|
| 1 | `read_element` / `get_all_values` en control de dirección (Edit, ComboBox o breadcrumb Value) | Texto debe coincidir con valor capturado pre-ACT |
| 2 | `element_exists` negativo popup | Flyout cerrado |
| 3 | `screenshot(scope=window)` | Evidencia; no sustituir paso 1 |

**Prohibido en VERIFY de ruta:** `find_element(name=<segmento o ruta completa>, role=Toolbar)` — rol incorrecto para migas Win11; dispara barrido UIA lento en miss.

**Tras fricción:** `repo_hints_set` — `nota: address flyout — read_element verify, no Toolbar find post-Escape`.

## Contexto del turno

- Lab `escritorio-windows-2026-09-10`, execute **F-86** `met` WARN.
- `mcp-usage.jsonl`: invoke 1447 ms ok; find_element Toolbar **33219 ms** slow.
- `improvements.jsonl`: workaround read_element + element_exists; fix_in_cycle not_attempted.

## Test de abstracción (L3)

Shell Win32 con barra de dirección y flyouts de historial (Explorador, diálogos Abrir) — no IDs de producto interno.

## Verificación de duplicados

| Archivo | Acción |
|---------|--------|
| `20260910_195900_explorer-breadcrumb-flyout-verify-routing` | **Merge al implementar** — añadir sub-bloque «Ubicaciones anteriores» post-Escape |
| `20260910_211830_ribbon-flyout-dismiss-verify-negative-only` | Complemento — verify negativo genérico cinta/flyout |
| `20260910_195126_find-element-name-search-negative-wall-clock` | Código — acota miss; no reemplaza routing read_element |

## Esfuerzo observado

~33 s en una sola VERIFY innecesaria; invoke flyout dentro de umbral OK.

## Criterios de aceptación (mantenedor)

- [ ] F-86 re-ejecutable: VERIFY ruta <3 s sin `find_element` Toolbar.
- [ ] Tres patrones flyout dirección documentados: breadcrumbs SplitButton, botón historial, menú contextual (MenuItem).
- [ ] Sin duplicar spec de `negative_fast` en skill (permanece en propuesta código).

## Beneficios futuros

Matriz lab deja WARN SLOW en F-86/F-08 familia; agente no confunde verify de ruta con búsqueda global por texto de carpeta.

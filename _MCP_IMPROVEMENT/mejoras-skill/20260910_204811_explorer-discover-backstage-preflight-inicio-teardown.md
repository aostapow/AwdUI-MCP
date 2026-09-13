# Explorer discover backstage — preflight búsqueda y salida TabItem Inicio

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 20:48:11 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | `awdui-mcp-automejora/references/evaluacion-lab.md` § discover subárbol; patrón nuevo `patterns/win32-explorer-ribbon.md` (merge con homónimos) |
| **Tipo de gap** | routing_tool |
| **Nivel** | L4 |
| **Versión MCP** | v0.4.0 (check_version 2026-09-10, up to date) |

## Resumen

**Problema:** En `discover_flows` **subárbol F-85** (backstage Pestaña Archivo), el inventario vía `get_snapshot` fue correcto (178 nodos, Lugares frecuentes encolados como F-117..F-134), pero el **teardown** falló al volver a la vista carpeta: `invoke_element` / actuación sobre **TabItem «Inicio»** no cerró el backstage; **Escape** fue parcial y quedó **modo búsqueda residual** («Cerrar búsqueda» ~1136 ms en el mismo pass). Sin preflight de búsqueda, el árbol mezcla cinta contextual de búsqueda con navegación Archivo/backstage.

**Solución:** (1) **Preflight** antes de abrir Archivo o discover backstage: si `element_exists` / snapshot previo muestra botón «Cerrar búsqueda» o foco en `SearchEditBox` tras F-10/F-42, cerrar búsqueda **una vez** (`invoke_element` «Cerrar búsqueda» o Escape + verify sin cinta Herramientas de búsqueda). (2) **Salida backstage:** localizar TabItem **Inicio de la cinta de navegación** (no ítems del panel Archivo) con `role=TabItem` + `discover_control_interaction`; actuar con SelectionItem (`click_element` / `invoke_element` según hint); **verify** con probe lab (`ListItem` archivo probe o ausencia de panel «Lugares frecuentes» / Menu backstage), no solo éxito de invoke. (3) **Fallback ordenado:** Escape → verify probe → si persiste backstage, repetir Inicio acotado; no encadenar find global por nombre «Inicio» sin role.

**Dónde:** `evaluacion-lab.md` — subsección «Discover subárbol — Explorer backstage (Archivo)»; cross-ref `patterns/active-window.md` y `20260910_195330_discover-subtree-search-ribbon-splitbutton-routing.md`.

## Contexto del turno

- Lab `escritorio-windows-2026-09-10`, `discover-F-85`, HWND lab Explorador.
- OBS: `click_element` Pestaña Archivo ~941 ms; `get_snapshot` backstage + frecuentes.
- ACT: encolar **F-117..F-134** (18 flows); `F-85.subtree_discovered=true`; `validate_flows` 134 OK.
- VERIFY: screenshot `_44.png`; **TabItem Inicio** act fail; Escape parcial; **Cerrar búsqueda** 1136 ms.
- `improvements.jsonl`: workaround Escape + Cerrar búsqueda; `objective_met` sigue false; cola execute F-98, F-106, F-43, F-29.

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| Modo búsqueda residual antes/durante discover Archivo | routing_tool | L4 | **Este archivo** (preflight) |
| TabItem Inicio no cierra backstage; verify ausente | routing_tool + deteccion | L4 | **Este archivo** (scope + verify) |
| Encolado F-117..134 desde snapshot | — | — | Ejecución correcta |
| `invoke_element` ya expone SelectionItem | ejecucion parcial | — | Falta **scope** y verify, no necesariamente código nuevo |

No es `sintoma_app` puntual: backstage Archivo y cinta búsqueda son patrón Win32 Explorer replicable.

## Texto propuesto

### Preflight — cerrar búsqueda antes de discover backstage

1. Tras cualquier flujo que tocó `SearchEditBox` (F-10, F-42, discover subárbol búsqueda):
   - `get_focused_element` o snapshot ligero: ¿cinta «Herramientas de búsqueda» / botón «Cerrar búsqueda» visible?
   - Si sí → `invoke_element(name="Cerrar búsqueda", role=Button)` **o** Escape + confirmar ausencia del botón (<2 s; no `find_element` negativo largo).
2. Solo entonces `invoke_element` / click **Pestaña Archivo** y `discover_flows` subárbol F-85.

### Discover subárbol backstage — teardown a vista carpeta

1. Inventario: `get_snapshot(max_depth=5..6)` como en el turno (no sustituir por barridos `list_elements` duplicados).
2. Salir del backstage:
   - `discover_control_interaction` sobre **TabItem** «Inicio» de la **cinta principal** (Inicio | Compartir | Vista…), con `role=TabItem` explícito.
   - Aplicar método recomendado (SelectionItem / Invoke); **verify:** `element_exists` probe `awdui_probe_readonly.txt` **o** snapshot sin bloque «Lugares frecuentes» del panel Archivo.
3. Si act OK en UIA pero verify falla → tratar como **FAIL**, no met; no marcar F-85 teardown como OK solo por Escape.
4. Fallback: `{Escape}` una vez → verify probe; si modo búsqueda reaparece → preflight «Cerrar búsqueda» otra vez.

### Prohibido

- `find_element(name="Inicio")` sin `role=TabItem` con backstage abierto (homónimos en panel Archivo y cinta).
- Abrir Pestaña Archivo con «Cerrar búsqueda» aún visible sin cerrar búsqueda primero.

## Test de abstracción (L4)

Cualquier ventana `CabinetWClass` con ribbon Win32: salir de overlay tipo Archivo/Configuración usando TabItem de cinta + verify de contenido carpeta, no solo teclado.

## Verificación de duplicados

| Propuesta | Relación |
|-----------|----------|
| `20260910_195330_discover-subtree-search-ribbon-splitbutton-routing` | **Merge** al aplicar — inventario cinta búsqueda; este doc añade **preflight** y teardown backstage |
| `20260910_204145_discover-subtree-modal-teardown-snapshot-cancel` | Paralelo — modal `#32770`; mismo principio «teardown desde snapshot + verify» |
| `20260910_202215_explorer-ribbon-homonym-tabitem-button` | Complemento — homónimos TabItem/Button; Inicio suele ser solo TabItem pero scope importa |
| `20260905_210300_click-element-selectionitem-datitem` | Código — SelectionItem en act; verify Explorer puede reutilizar patrón sin nuevo patch si scope correcto |

## Esfuerzo observado

Discover-F-85: Archivo 941 ms, snapshot 178 nodos, 18 flows encolados, Cerrar búsqueda 1136 ms, Inicio fail + Escape parcial; `last_cycle.next` ejecutar F-98 y cerrar backstage si abierto.

## Beneficios futuros

- Discover backstage sin mezclar árbol de búsqueda residual.
- Teardown verificable (probe) alineado con `success_criteria` F-85 en `flows.json`.
- Menos workarounds Escape-only en matriz Escritorio.

## Criterios de aceptación

- [ ] Texto sin rutas lab salvo nombres genéricos Explorer/backstage/búsqueda.
- [ ] Replay discover-F-85: preflight + salida Inicio con verify probe < **3 s** total teardown (sin find negativo >3 s).
- [ ] Cross-ref en `evaluacion-lab.md` y opcional `win32-explorer-ribbon.md` al implementar.

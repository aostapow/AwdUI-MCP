# Explorer F-23 met con workaround — gate repo + playbook F-93..96 (SharePickerFlyout)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 20:32:15 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | `awdui-mcp-automejora/references/evaluacion-lab.md` + `references/patterns/object-repository.md` |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Versión MCP** | v0.4.0 (up to date) |

## Resumen

**Problema:** **F-23** pasó a `met` con workaround (clic ListItem + clic Enviar por coordenadas /
`get_element_bounds` + centro), verify vía `get_snapshot` / `SharePickerFlyout` UIA. El turno **no**
invocó `repo_hints_set` ni `repo_capture` de los IDs descubiertos (`SharePickerFlyout`,
`CopyFileButton`, `SuggestedContactGridView`). Se encolaron **F-93..97** como subárbol de F-23;
sin persistir hints, **F-93..96** repetirán apertura frágil y `invoke_element` sobre **ListItem**
incorrecto (~**3796 ms** SLOW, verify fail en invoke).

**Solución:**

1. **Gate lab (met + workaround):** Si `coverage.json` o notas del flujo registran `workaround`,
   el cierre del paso **no** es solo screenshot — obligatorio en el mismo turno (o inmediatamente
   después): `repo_capture` o `repo_hints_set` con `ensure_minimal` (cuando exista tool
   `20260910_200820`) para rutas `Escritorio/Explorer/SharePicker/*` y hint
   `metodo_preferido: click_element` + `verify_automation_id: SharePickerFlyout` en el botón
   Enviar del grupo cinta.
2. **Playbook F-93 (entry flyout):** Precondición = F-23 cumplido **y**
   `element_exists(automation_id=SharePickerFlyout)` o nodo en `get_snapshot` — **sin** re-invoke
   ListItem de ItemsView.
3. **Hijos F-94..96:** `list_elements` / `find_element` scoped por `ancestor_automation_id=SharePickerFlyout`
   (o `name_contains` estable del discover); **no** coords salvo último recurso documentado en hints.
4. **F-97:** permanece `cancelled` (política proximidad) — no ejecutar.

**Dónde:** `evaluacion-lab.md` § cierre execute_flow (workaround → repo); ampliar
`object-repository.md` tabla «Cuándo escribir hints» con fila **met+workaround en lab**;
merge al implementar con `20260910_202708` (ACT/VERIFY Share, sin ListItem vista archivos).

## Contexto del turno

- Lab `escritorio-windows-2026-09-10`: **F-92** `met` (ViewButtonsGroup, UIA limpia).
- **F-23** `met` con workaround; `invoke_element` **ListItem** **3796 ms** SLOW, verify invoke fail;
  verify flyout OK con `SharePickerFlyout` en snapshot.
- **discover_flows** subárbol F-23 → **F-93..97** (F-97 cancelled).
- Sin `repo_hints_set` en el turno; blockers **Teams** sin cambio (`teams_perfect` false).

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| met F-23 sin repo tras coords | routing_tool | L3 | **Sí (este archivo)** |
| ListItem vista vs cinta Enviar | routing_tool | L4 | `20260910_202708` — merge ACT |
| invoke ListItem 3796 ms | routing_tool / performance | L3 | No archivo nuevo — causa = target incorrecto; no duplicar `214800` (Electron probe) |
| repo_hints_set object not found | tool_gap | L4 | `20260910_200820` vigente |
| F-93..97 encolado OK | — | — | No — discover correcto |
| Teams cold WebView | performance | L3 | Backlog state `blockers` — sin propuesta nueva |

## Texto propuesto

### Gate workaround → repositorio (lab)

Tras marcar un flujo `met` si la evidencia incluye `workaround`, `coords`, o `click_element` sin
`automation_id` estable en el ACT:

1. `repo_capture` del control que **sí** funcionó (Button Enviar, `SharePickerFlyout`, etc.).
2. `repo_hints_set` con `metodo_preferido`, `verify_automation_id`, `nota:` con IDs de
   `discovery_signals` del subárbol hijo.
3. Solo entonces encolar o ejecutar entries hijas (`parent_id` = flujo padre).

### Execute F-93..96 (SharePickerFlyout)

| Paso | Acción |
|------|--------|
| Pre | `element_exists(automation_id=SharePickerFlyout)` — si fail, repetir ACT F-23 vía **Button** cinta (ver `202708`), no ListItem ItemsView |
| OBS | `get_snapshot(max_depth=4)` o `list_elements(role=Button|List|Text, ancestor…)` |
| ACT hijos | `invoke_element` / `click_element` solo nodos bajo flyout |
| VERIFY | Panel lateral visible; `Escape` cierra sin envío |
| Cierre | `repo_hints_set` si hubo nuevo workaround |

## Test de abstracción (L3)

Cualquier lab con flujo padre `met` por workaround y subárbol discover encolado: la lección debe
vivir en repo antes de hijos — no específico de «Compartir» salvo ejemplos de ruta.

## Verificación de duplicados

| Propuesta | Acción |
|-----------|--------|
| `20260910_202708_explorer-share-f23-listitem-scope-light-dismiss-verify` | **Merge** — añadir gate repo + tabla F-93 |
| `20260910_200820_repo-hints-set-missing-path-actionable-error` | Complementaria — tool; skill referencia `ensure_minimal` |
| `patterns/object-repository.md` | Ya documenta workaround → hints; **reforzar** gate lab met+workaround |

## Esfuerzo observado

F-23: invoke ListItem lento + verify fail; éxito solo con coords y snapshot flyout; discover
F-93..97 sin fricción; omisión repo en cierre.

## Criterios de aceptación (mantenedor)

- [ ] Texto aplicable sin obligar coords literales del run.
- [ ] Gate `perfect` / `validate_perfect_gate` puede leer flag workaround sin repo (opcional G9 futuro).
- [ ] Re-execute F-93 con flyout abierto programáticamente (sin coords) tras hints.

## Beneficios futuros

F-93..96 ejecutables sin repetir 3.8 s en ListItem erróneo; `repo-snapshot.json` alineado con
subárbol Share; menos regresión al retomar lab Escritorio.

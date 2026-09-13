# discover_flows raíz: get_snapshot como whitelist — sin find especulativo

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 20:27:30 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | `awdui-mcp-automejora/references/evaluacion-lab.md` § discover raíz |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Versión MCP** | v0.4.0 (check_version 2026-09-10, up to date) |

## Resumen

**Problema:** En `discover_flows` **raíz** (Explorador carpeta lab, pass-3), el agente ejecutó
`get_snapshot(max_depth=5)` (**81 nodos**, señales útiles) y encoló bien **F-85..F-88**, pero además
`find_element` por **«Panel de navegación»** (`SplitButton`) → **NOT FOUND ~8985 ms** (`find_neg`).
Ese control solo aparece con la cinta **Vista** activa; no estaba en el snapshot ni en
`discovery_signals` del pass.

**Solución:** Tras **una** pasada de inventario en discover raíz (`get_snapshot` o
`list_elements` acotado), tratar el resultado como **whitelist**: (1) encolar `entry` solo para
pares `(name, role)` / `automation_id` devueltos; (2) **prohibido** `find_element` / `find_elements_fuzzy`
por chrome contextual no listado (ribbon de otra pestaña, paneles opcionales); (3) si el mapa de lab
anticipa el control, anotar en flows `cancelled` + nota «requiere contexto X» — no probe con ladder.
Complementa inventario modal (`201511`) y Vista execute (`200930`).

**Dónde:** `evaluacion-lab.md` — subsección «Discover raíz — snapshot gate»; cross-ref
`patterns/mcp-value-filter.md`.

## Contexto del turno

- Lab `escritorio-windows-2026-09-10`, modo `discover_flows`, scope **raíz**.
- `get_snapshot` depth 5 OK; `find_pos` ~881 ms; `find_neg` Panel navegación **8985 ms**;
  probe readonly **452 ms**; screenshot `awdui_1789082576279_27.png`.
- Encolados: F-85 Pestaña Archivo, F-86 Ubicaciones anteriores, F-87 Minimizar cinta, F-88 Actualizar (F5).
- Cola lab **88 flujos** (`flows_progress.total` 84→88 tras pass); `subtree_discovered: false` en entries nuevos.
- `improvements.jsonl` / `coverage.json`: workaround ya citado — find solo señales vistas en snapshot.

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| find_neg Panel navegación 9s | performance | L4 | Código vigente `195126_find-element-name-search-negative-wall-clock` (no duplicar) |
| find fuera de whitelist post-snapshot | routing_tool | L3 | **Este archivo** |
| Encolado F-85..88 desde snapshot | — | — | Ejecución correcta; no proponer |

No es `ejecucion` pura: `evaluacion-lab` no explicita gate raíz tras `get_snapshot`; el agente mezcló inventario OK con probe especulativo.

## Texto propuesto

### Discover raíz — paso obligatorio snapshot gate

1. `set_target_window` ventana lab; opcional `ascii_ui_view` / `detection_health`.
2. **Inventario único:** `get_snapshot(max_depth=5)` *o* `list_elements(max_depth=6, role=Button|SplitButton|TabItem)` — registrar conteo y roles.
3. **Encolar** `kind: entry` solo desde nodos del inventario (coords/name en `discovery_signals`).
4. **Prohibido en el mismo pass:** `find_element(name=…)` si el par `(name, role)` no apareció en el inventario del paso 2.
5. Controles conocidos context-dependent (p. ej. paneles de pestaña Vista/Inicio no activa): `cancelled` + nota, o hijo bajo `execute_flow` del entry que abre ese contexto — **no** find raíz.
6. Miss esperado (si aplica propuesta código): abortar rápido con `find_path=negative_fast`; no repetir ladder en discover.

**Preferencia snapshot vs find:** En discover raíz, `get_snapshot` es inventario; `find_element` solo para **confirmar** un nodo ya listado (automation_id estable) o post-`invoke` subárbol — no para descubrir chrome ausente del snapshot.

## Test de abstracción (L3)

Cualquier lab con discover raíz (Notepad menús visibles, Calc NavView con un modo activo): whitelist post-inventario evita find 8–30 s en controles de otro contexto.

## Verificación de duplicados

| Propuesta | Relación |
|-----------|----------|
| `201511_discover-owned-modal-inventory-before-find` | **Consolidar** al aplicar: un bloque «Inventario pre-find» (raíz + modal + subárbol) |
| `200930_explorer-vista-ribbon-vistas-verify-routing` | Complemento execute/verify Vista; no sustituye gate raíz |
| `195126_find-element-name-search-negative-wall-clock` | Performance; skill reduce llamadas; código acota wall-clock |

## Esfuerzo observado

~9 s desperdiciados en un probe raíz; pass global OK (4 entries, live_verify ok). Acumulado lab discover sigue bloqueando G6 eficiencia hasta fix P1 find_neg.

## Criterios de aceptación

- [ ] Texto sin depender solo de «Panel de navegación»; patrón whitelist genérico.
- [ ] Replay discover raíz pass-3: sin `find_element` >3 s por nodos ausentes del snapshot.
- [ ] Referencia cruzada con modal inventory (`201511`) en un solo § `evaluacion-lab.md`.

## Beneficios futuros

- Alinea discover raíz con OBS→ACT→VERIFY: observación = snapshot, acción = enqueue, sin búsquedas especulativas.
- Reduce latencia discover sin esperar solo `negative_fast` en servidor.

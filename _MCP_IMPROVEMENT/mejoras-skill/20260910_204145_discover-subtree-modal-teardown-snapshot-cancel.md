# discover_flows subárbol modal: teardown desde snapshot (sin find Cancel en padre)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 20:41:45 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | `awdui-mcp-automejora/references/evaluacion-lab.md` § discover subárbol |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Versión MCP** | v0.4.0 (check_version 2026-09-10, up to date) |

## Resumen

**Problema:** Tras `discover_flows` **subárbol F-30** (diálogo Propiedades), el agente encoló F-103..F-110
desde `get_snapshot` correcto (148 nodos, 5 tabs), tomó screenshot de verify y cerró con
`find_element(name="Cancelar")` **sin** acotar al modal → **NOT FOUND ~7006 ms** (`cancel_fail` en
`evidence.jsonl`). En el mismo pass, `invoke_element` TabItem «General» / contexto Inicio tardó **2414 ms**
(`tab_inicio` WARN SLOW).

**Solución:** Tras inventario snapshot en modal owned: (1) **teardown** solo con nodos ya vistos —
`invoke_element`/`click_element` en `Button` Cancelar (`id=2` típico) o `send_keys` Escape **después**
de `focus_window` título modal / HWND del `#32770`; (2) **prohibido** `find_element(Cancelar)` desde
scope Explorador padre; (3) si Cancel no está en snapshot, Escape una vez y `list_windows` confirma cierre.
Complementa inventario pre-find (`201511`) y whitelist raíz (`202730`).

**Dónde:** `evaluacion-lab.md` — subsección «Discover subárbol — cierre modal»; cross-ref
`patterns/active-window.md`.

## Contexto del turno

- Lab `escritorio-windows-2026-09-10`, `discover-F-30`, scope subárbol Propiedades.
- OBS: reopen Propiedades; `get_snapshot` tabs General..Personalizar + «Versiones anteriores».
- ACT: enqueue **F-103..F-110** (6 pending, F-109 Aplicar / F-110 OK **cancelled** por política).
- VERIFY: `_41.png`; teardown con find Cancel fallido **7006 ms**; veredicto OK WARN SLOW.
- `improvements.jsonl`: workaround `focus_window` Propiedades o Escape; **F-106** candidato fixture **F-29**
  (Historial ribbon `is_enabled=False` — ruta versiones vía pestaña Propiedades).

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| find Cancel 6s post-discover | routing_tool + performance | L3/L4 | Skill **este archivo**; código `201130` + `195126` |
| TabItem ~2.4s en modal | performance | L3 | Backlog invoke/treeitem; no archivo nuevo |
| Encolado F-103..110 desde snapshot | — | — | Ejecución correcta |
| F-106 → desbloqueo F-29 | routing_tool (lab orden) | L2 | **Consolidar** en `203650` nota operativa al aplicar |

No es `ejecucion` pura: la metodología no detalla **cierre** discover en modal con mismo patrón que inventario.

## Texto propuesto

### Discover subárbol — cierre modal (teardown)

1. Tras paso VERIFY (screenshot opcional), el modal sigue abierto: anotar HWND/título de paso OBS.
2. `focus_window` modal (hasta `owned_modal` en servidor — propuesta `201130`).
3. Cerrar en orden:
   - Si el inventario del pass listó `Button: Cancelar` / `id=2` → `invoke_element` con `automation_id` o name+role **sin** nuevo `find_element` global.
   - Si no → `send_keys` `{Escape}`; confirmar con `list_windows` (modal ausente).
4. **Prohibido:** `find_element(Cancelar)` con target padre Explorador tras discover subárbol.
5. Miss de búsqueda en teardown: no depth ladder; usar Escape (evita 6–30 s).

### Orden lab Escritorio (nota al aplicar `203650`)

- Ejecutar **F-106** (TabItem Versiones anteriores) **antes** reintentar **F-29** cuando el probe ribbon
  «Historial» quedó `blocked_fixture` — misma capacidad funcional por UI alternativa en Propiedades.

## Test de abstracción (L3)

Cualquier discover subárbol en modal `#32770` mismo PID (Propiedades archivo/carpeta, Buscar, permisos):
teardown desde whitelist/Escape, no find en ventana padre.

## Verificación de duplicados

| Propuesta | Relación |
|-----------|----------|
| `201511_discover-owned-modal-inventory-before-find` | **Merge** al aplicar: inventario + teardown en un § modal |
| `202730_discover-root-get-snapshot-whitelist-find-probes` | Paralelo raíz vs subárbol modal |
| `201130_owned-modal-auto-scope-without-foreground` | Código — reduce necesidad de focus manual |
| `195126_find-element-name-search-negative-wall-clock` | Performance si igual se llama find por error |
| `203650_explorer-ribbon-enabled-preflight-skip-verify-find` | Ampliar nota F-106↔F-29 al implementar |

## Esfuerzo observado

Discover-F-30: `tab_inicio` 2414 ms, `props` 553 ms, `cancel_fail` 7006 ms; 8 flows encolados; cola lab ~110.

## Criterios de aceptación

- [ ] Texto genérico (Propiedades + otro modal sistema), no solo Explorador.
- [ ] Replay discover-F-30: cierre modal < **1 s** (invoke Cancel o Escape) sin `find_neg` >3 s.
- [ ] Referencia cruzada F-106/F-29 en nota lab sin hardcodear único flujo en skill genérica.

## Beneficios futuros

- Cierra discover subárbol sin latencia fantasma en G6 eficiencia.
- Alinea teardown con snapshot gate (misma whitelist OBS→VERIFY→cierre).

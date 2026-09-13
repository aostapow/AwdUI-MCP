# Discover raíz: preflight búsqueda solo si snapshot — sin find «Cerrar búsqueda»

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 20:50:50 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | `awdui-mcp-automejora/references/evaluacion-lab.md` § discover raíz |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Versión MCP** | v0.4.0 (check_version 2026-09-10, up to date) |

## Resumen

**Problema:** En `discover_flows` **raíz pass-6** (vista Inicio, `get_snapshot` **122 nodos**, encolado correcto **F-135..F-149**), el agente ejecutó `find_element(name="Cerrar búsqueda")` como preflight aunque **no** había modo búsqueda activo → **NOT FOUND ~25269 ms** (`find_neg` SLOW). El inventario del pass no listaba `SearchEditBox` ni botón «Cerrar búsqueda»; el probe violó el gate snapshot y bloqueó G6 eficiencia con `objective_met` false.

**Solución:** Unificar preflight búsqueda Explorer en discover **cualquier pass (raíz o subárbol)**: (1) leer el inventario del paso (`get_snapshot` / señales del pass); (2) **solo si** aparece `SearchEditBox` o `Button: Cerrar búsqueda`, cerrar con `invoke_element` acotado (<2 s); (3) si **ausente**, **omitir** preflight — no `find_element`, no `element_exists` largo; (4) encolar entries solo desde whitelist (Organizar, breadcrumbs, árbol) como en pass-6.

**Dónde:** Merge al aplicar con `20260910_202730_discover-root-get-snapshot-whitelist-find-probes.md` (§ snapshot gate) y `20260910_204811_explorer-discover-backstage-preflight-inicio-teardown.md` (preflight búsqueda antes de Archivo).

## Contexto del turno

- Lab `escritorio-windows-2026-09-10`, `discover_flows` raíz **pass-6**, `kind: entry` only.
- OBS: `get_snapshot` 122 nodos — cinta Inicio (Organizar Mover a/Copiar a), barra Atrás/Adelante, breadcrumbs, árbol Este equipo/OneDrive/Red.
- ACT: encolar **F-135..F-149** (15 flows; F-149 Eliminar `cancelled`); `validate_flows` 149 OK; screenshot `awdui_1789084191968_45.png`.
- Fricción: `find_element` neg «Cerrar búsqueda» **25269 ms** sin modo búsqueda (`improvements.jsonl` discover-root-pass6); `TabItem` Inicio invoke fail recurrente (backlog teardown); repo vacío — sin `repo_hints_set` (backlog `200820`).

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| find_neg Cerrar búsqueda 25s sin búsqueda | performance | L4 | Código `195126_find-element-name-search-negative-wall-clock` — **no duplicar** |
| find preflight fuera de whitelist | routing_tool | L3 | **Este archivo** (consolidación) |
| Encolado F-135..149 desde snapshot | — | — | Ejecución correcta |
| TabItem Inicio invoke fail | routing_tool | L3 | Merge `204811` al aplicar |
| repo_hints_set omitido | ejecucion | — | Backlog `200820` |

Pass-5 demostró discover raíz **sin** `find_neg` cuando se respeta inventario; pass-6 regresa al anti-patrón preflight con `find_element`.

## Texto propuesto

### Preflight modo búsqueda (discover Explorer — raíz y subárbol)

1. Tras inventario del pass, **grep mental** en nodos: `SearchEditBox`, `Cerrar búsqueda`, cinta «Herramientas de búsqueda».
2. **Si ninguno** → continuar discover / encolar **sin** preflight búsqueda.
3. **Si presente** → `invoke_element` «Cerrar búsqueda» o Escape + verify en snapshot (<2 s); **prohibido** `find_element` por nombre si el botón no estaba en el inventario del paso 1.
4. Aplica antes de discover backstage (Archivo), pass raíz Organizar/breadcrumbs (pass-6), y subárbol búsqueda (F-42).

**Prohibido:** `find_element(Cerrar búsqueda)` cuando el snapshot del mismo pass no listó ese control (aunque turnos anteriores hayan usado búsqueda).

## Test de abstracción (L3)

Cualquier ventana con modo contextual opcional (Notepad Buscar, Teams overlay): preflight condicionado al inventario del pass, no find especulativo.

## Verificación de duplicados

| Propuesta | Relación |
|-----------|----------|
| `20260910_202730_discover-root-get-snapshot-whitelist-find-probes` | **Merge** — gate raíz general |
| `20260910_204811_explorer-discover-backstage-preflight-inicio-teardown` | **Merge** — preflight antes Archivo |
| `20260910_195126_find-element-name-search-negative-wall-clock` | Performance wall-clock miss |
| `20260910_200820_repo-hints-set-missing-path-actionable-error` | Paralelo — repo tras discover OK |

## Esfuerzo observado

~25 s en un solo miss durante pass-6 otherwise limpio; acumulado lab + criterio «slow sin waiver» mantiene `objective_met` false.

## Criterios de aceptación

- [ ] Un solo § en `evaluacion-lab.md` (merge 202730 + 204811 + este ítem).
- [ ] Replay discover pass-6: cero `find_element` >3 s; preflight búsqueda omitido cuando snapshot sin SearchEditBox.
- [ ] Tras implementar `195126`: miss accidental p95 <3 s aun si el agente viola la skill.

## Beneficios futuros

- Pass raíz puede encolar 15+ entries sin latencia fantasma.
- Alinea preflight búsqueda con OBS→ACT: observación = snapshot, no ladder find negativo.

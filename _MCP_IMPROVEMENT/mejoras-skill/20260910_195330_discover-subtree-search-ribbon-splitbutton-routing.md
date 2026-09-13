# discover_flows subárbol — cinta contextual búsqueda (SplitButton, no doble Button)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 19:53:30 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | `awdui-mcp-automejora/references/evaluacion-lab.md` |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Versión MCP** | 0.4.0 |

## Resumen

**Problema:** En `discover_flows` **subárbol** F-10 (Explorador — cinta «Herramientas de búsqueda» abierta),
el agente ejecutó **dos** `list_elements(role=Button, max_depth=4/6)` consecutivos (**~12.0 s + ~12.5 s**,
~24.5 s wall-clock) para encolar F-38..F-50, pese a que la UI ya exponía **6 SplitButton** de refinamiento
y `find_element` por `automation_id`/name conocidos respondía en **<400 ms** (workaround positivo del turno).

**Solución:** En B3/B4 cuando el subárbol es **pestaña contextual de cinta** (TabItem + toolbar de búsqueda):
(1) un único barrido `list_elements(role="SplitButton", max_depth=4)` **o** `list_elements(role="Button", ancestor_automation_id=<toolbar>)` si está documentado;
(2) encolar acciones desde ese listado + `find_element` puntual con ids estables — **no** repetir barrido global `Button`;
(3) tras timing ≥3 s → `repo_hints_set` con `latencia:` / `nota: discover F-XX search ribbon`.

**Dónde:** `evaluacion-lab.md` § Modo B pasos B3–B4 + tabla «Subárbol cinta contextual»; enlace desde
`patterns/control-catalog.md` § SplitButton (ExpandCollapse en ribbon Win32).

## Contexto del turno

- `discover-F-10`: `subtree_discovered=true`; **13** flujos encolados **F-38..F-50** (10 pending, 3 cancelled).
- Evidence: `list_button` 12035 ms + 12513 ms; `invoke_cerrar` 771 ms; `probe` 335 ms; screenshot `_9.png`.
- `improvements.jsonl`: workaround `find_element` por automation_id/name en ribbon búsqueda — positivos <400 ms.

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| Doble `list_elements` Button ~12 s c/u | routing_tool | L3 | Sí (este archivo) |
| `find_element` positivos <400 ms | ejecucion (vía correcta) | — | No — reforzar en skill |
| Latencia acumulada vs gate G6 (p95 ≤2000 ms discover) | performance | L3 | Mitigado por routing; backlog perf Explorer no duplicado aquí |

Complementa `20260910_195126_discover-subtree-flyout-menuitem-scan` (flyout MenuItem) — este bloque es **cinta contextual Win32** (SplitButton + SearchEditBox).

## Texto propuesto

### Subárbol con cinta contextual / búsqueda (discover B3–B4)

Tras B2 (pestaña contextual visible; p. ej. «Herramientas de búsqueda»):

1. **Inventario acotado:** `list_elements(role="SplitButton", max_depth=4)` — refinadores visibles en la cinta.
2. **Opcional complemento:** `find_element(automation_id=…)` / `find_element(name=…, role=Button|SplitButton)` **solo** para affordances ya vistos en `discovered.yaml` o en un listado previo del mismo turno — miss rápido; no sustituir inventario por búsquedas negativas largas (ver propuesta código `find-element-name-search-negative-wall-clock`).
3. **Prohibido:** dos o más `list_elements(role="Button")` sin `ancestor_automation_id` del toolbar de búsqueda en el mismo discover.
4. **Encolar:** un `action` por SplitButton/refinador coherente; dedupe por `discovery_signals`; marcar padre `subtree_discovered=true` al cerrar barrido.
5. Tras WARN slow (≥3000 ms) en list: `repo_hints_set(append=true)` — `nota: discover search ribbon — SplitButton-first, no double Button`.

## Test de abstracción (L3)

Aplica a Office ribbon contextual, Explorador pestañas Compartir/Vista/Copiar, cualquier Win32 toolbar contextual — no solo lab escritorio.

## Verificación de duplicados

| Propuesta | Acción |
|-----------|--------|
| `20260910_195126_discover-subtree-flyout-menuitem-scan` | Hermana; merge opcional en evaluacion-lab § Subárbol |
| `20260910_195126_find-element-name-search-negative-wall-clock` | Complemento — negativos; este ítem — positivos + no doble list |
| Backlog `max-depth` / `list-elements-default` performance | No duplicar issue perf genérico |

## Esfuerzo observado

~24.5 s en dos listados Button evitables; encolado de 13 flujos OK pero costo discover incompatible con gate G6.

## Criterios de aceptación (mantenedor)

- [ ] Texto sin rutas lab concretas salvo ejemplo genérico «cinta búsqueda».
- [ ] Distinción clara flyout (MenuItem) vs cinta contextual (SplitButton).
- [ ] Próximo discover subárbol tipo F-10: un list SplitButton + hints si slow; sin segundo Button global.

## Beneficios futuros

Discover subárbol en Explorer escala sin ~25 s de barrido duplicado; alinea agente con workaround ya probado (`find_element` positivos).

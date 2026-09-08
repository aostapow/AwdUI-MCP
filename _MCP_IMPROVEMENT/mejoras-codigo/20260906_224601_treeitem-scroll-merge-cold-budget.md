# list_elements TreeItem: presupuesto cold scroll-merge < 2000 ms

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-06 22:46:01 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | `detection/backends/uia_backend.py`, `detection/orchestrator.py` |
| **Tool afectada** | `list_elements`, `set_target_window` |
| **Tipo de gap** | performance |
| **Nivel** | L4 |
| **Impacto** | alto |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** Scroll-merge en `_collect_treeitem_findall` resuelve virtualización (49
TreeItems incl. offscreen) pero cold path **3398 ms** excede gate `teams_perfect`
(**< 2000 ms** p95 TE-02). Cache repeat **0 ms** OK. Regresión vs turno 5 fast FindAll
(**578 ms**, 16 visibles) — el costo del sweep completo es el blocker residual.

**Causa raíz:** El sweep hace hasta: SetScrollPercent 100 + re-FindAll + SetScrollPercent
0 + re-FindAll + **5** iteraciones ScrollPattern down + hasta **2** keyboard nudge
(PageDown) con sleeps 80–120 ms cada uno. Sin wall-clock budget ni early-exit cuando
`target_more` ya se alcanza tras primer paso.

**Solución:**

1. **Wall-clock budget** configurable (default **2500 ms** hard cap, objetivo **1800 ms**
   soft) en `_collect_treeitem_findall`; abortar sweep y devolver `merged` parcial si
   budget agotado (con `scroll_merge_truncated: true`).
2. **Early exit:** tras SetScrollPercent 0→100→0, si `len(merged) >= target_more` saltar
   loop de 5 + keyboard.
3. **Reducir sleeps** a 40 ms cuando framework=electron (medido en turno).
4. **Prefetch alineado:** en `set_target_window` Electron, warm scroll-merge async con
   mismo budget; TE-02 cold lee cache uia_tree_cache (scope `treeitem:findall:{cap}`).
5. Parámetro opcional `list_elements(..., realize_virtualized: bool = True)` — harness
   TE-02 default true; agente puede pasar `false` para fast path 16 visibles + `find_element`
   puntual (documentar trade-off).
6. JSON: `scroll_merge_ms`, `scroll_merge_phases`, `realize_virtualized`, `duration_ms`.

**Dónde:** `uia_backend._collect_treeitem_findall`, `orchestrator.list_elements`,
`target_window._prefetch_electron_treeitem_cache`, `tests/test_uia_find_performance.py`,
`docs/MCP_TOOLS_REFERENCE.md`.

## Contexto del turno

| Métrica | Turno 5 | Turno 6 |
|---------|---------|---------|
| Cold list TreeItem | 578 ms, 16 items | **3398 ms**, 49 items |
| Virtualization gap | WARN 16 vs 23 | **Resuelto** (49 incl menur31) |
| Cache warm | 0 ms | **0 ms** |
| TE-03 | — | Nav OK; menur1r 12 s post-scroll |
| pytest | 15 passed | **16 passed** |
| teams_perfect | false | **false** (cold SLOW) |

## Cambio propuesto (pseudodiff)

```python
# uia_backend.py

_SCROLL_MERGE_SOFT_MS = 1800
_SCROLL_MERGE_HARD_MS = 2500

def _collect_treeitem_findall(self, window, cap: int, *, realize: bool = True) -> list:
    t0 = time.perf_counter()
    merged = self._findall_sidebar_treeitems(window, prune_left)
    if not realize or len(merged) >= target_more:
        return merged
    ...
    for phase in ("pct100", "pct0", "loop", "keyboard"):
        if (time.perf_counter() - t0) * 1000 > _SCROLL_MERGE_HARD_MS:
            self._scroll_merge_truncated = True
            break
        # phase body; break inner loops if len(merged) >= target_more
    self._scroll_merge_ms = int((time.perf_counter() - t0) * 1000)
    return merged
```

```python
# orchestrator.py

def list_elements(..., realize_virtualized: bool = True):
    ...
    return {
        ...,
        "scroll_merge_ms": getattr(backend, "scroll_merge_ms", None),
        "scroll_merge_truncated": getattr(backend, "scroll_merge_truncated", False),
        "realize_virtualized": realize_virtualized,
    }
```

## Verificación de duplicados

| Propuesta | Relación |
|-----------|----------|
| 223200 cache miss + collect_path | Cache repeat **resuelto** (0 ms); este ítem cubre **costo sweep** |
| 223500 virtualized gap | **Resuelto** funcionalmente — archivar; perf es tema separado |
| 222700 / 214500 cold perf | **Cerrar** tema pre-scroll-merge; merge archive con este si <2s validado |
| 213301 teams_perfect gate | **Extender** TE-02: 3398 ms sigue blocker |

**Acción mantenedor:** archivar 223200 (cache), 223500 (gap); una spec perf `treeitem-cold-budget`.

## Test de abstracción (L4)

Listas virtualizadas UIA/Electron: enumeración completa con presupuesto temporal — Slack,
VS Code tree, Discord channels; sin hardcode Teams.

## Esfuerzo observado

Breakthrough funcional (49 items) vs gate numérico; harness agentico paga ~3.4 s cada
cold TE-02 aunque cache amortiza repeticiones.

## Criterio de aceptación

- [ ] `tests/test_treeitem_scroll_merge_budget.py`: mock fases lentas → truncado < hard cap;
      `scroll_merge_truncated=true`.
- [ ] Live Teams: cold p95 < **2000 ms** con `realize_virtualized=true` y ≥45 TreeItems
      **o** documentar `realize_virtualized=false` fast path < 600 ms + find puntual.
- [ ] Prefetch `set_target`: segunda sesión cold < 2000 ms (cache hit scroll-merge).
- [ ] JSON incluye `scroll_merge_ms`, `duration_ms`, `cache_hit`.
- [ ] Sin regresión pytest 16+ passed; menur31 offscreen presente cuando realize=true.
- [ ] `MCP_TOOLS_REFERENCE.md` documenta parámetro `realize_virtualized`.

## Beneficios futuros

- Cierra blocker TE-02 latency para `teams_perfect`.
- Agente elige fast vs complete sin paths de 12 s alternativos.
- Telemetría `scroll_merge_ms` separa perf COM vs costo scroll.

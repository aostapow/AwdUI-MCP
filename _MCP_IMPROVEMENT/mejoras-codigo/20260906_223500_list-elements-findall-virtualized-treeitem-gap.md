# list_elements TreeItem: gap FindAll visible vs descendants offscreen (16 vs 23)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-06 22:35:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | `detection/backends/uia_backend.py`, `detection/orchestrator.py` |
| **Tool afectada** | `list_elements`, `realize_virtualized_item` |
| **Tipo de gap** | deteccion |
| **Nivel** | L4 |
| **Impacto** | medio |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** Tras fix P1 orchestrator (`_resolve_list_window_context` → clave
`{title}|{hwnd}|…` en lugar de `|0`), TE-02 live alcanza **538 ms** cold y **0 ms**
cache con path UIA `FindAll(TreeItem)`. Sin embargo el harness emite **WARN**:
FindAll devuelve **16** TreeItems visibles en viewport mientras un walk
`descendants(TreeItem)` (o conteo previo) reporta **23** chats `menur*` — gap por
virtualización Electron/WebView (items offscreen no materializados en FindAll).

**Causa raíz:** `_collect_treeitem_findall` prioriza una sola query COM
(`FindAll` + filtro bbox sidebar) que refleja el subárbol **actualmente
expuesto** por UIA, no la lista completa de chats virtualizados. Con
`include_offscreen=true` (default auto para TreeItem en orchestrator) el filtro
post-collect `_element_useful` no recupera nodos que UIA nunca devolvió en
FindAll.

**Solución:**

1. Tras FindAll, **spot-check** con `window.descendants(control_type="TreeItem",
   depth=cap)` (budget ≤ 500 ms o solo si `findall_count < _SIDEBAR_TREE_MIN_ITEMS
   + margin`) — si `descendants_count > findall_count + 2`, marcar
   `virtualized_gap=true` y opcionalmente **complementar** con descendants
   (dedupe por `runtime_id`) o invocar scroll incremental en contenedor Tree
   (`scroll_element` / `ScrollPattern` en sidebar) + segundo FindAll.
2. Respuesta JSON: `findall_count`, `enumeration_count`, `virtualized_gap`,
   `collect_path: "findall"|"findall+descendants"|"sidebar_scroll"`.
3. **No** degradar p95 cold por defecto: complemento descendants solo si gap >
   umbral o agente pasa `enumerate_all=true` (nuevo parámetro opcional en
   `list_elements`).
4. Documentar en `MCP_TOOLS_REFERENCE.md`: para chat offscreen, preferir
   `find_element(automation_id=menur*)` / `find_element(name~)` — no exigir
   `list_elements` count == total chats.
5. Skill `teams-mcp-harness` TE-02: criterio de éxito = target chat presente +
   latencia < 2000 ms — no count absoluto 23 (ver consolidación con 213301).

**Dónde:** `uia_backend._collect_typed_role_elements`, `_collect_treeitem_findall`;
`orchestrator.list_elements`; tests `tests/test_uia_find_performance.py`;
`docs/MCP_TOOLS_REFERENCE.md`.

## Contexto del turno

| Métrica | Turno anterior (cache miss) | Turno actual (breakthrough) |
|---------|----------------------------|----------------------------|
| `list_elements(TreeItem)` cold | 12058 ms, repeat 11821 ms uia | **538 ms** OK |
| Segunda list misma sesión | miss (`|0` cache key) | **0 ms** cache |
| TE-05 invoke | OK | **OK** |
| TreeItem count FindAll | 23 (path lento) | **16** visible WARN vs **23** descendants |
| Root cause fix | — | `_resolve_list_window_context` + UIA FindAll first |
| pytest | 31 passed | `test_orchestrator_cache.py` session target |
| teams_perfect | false | **false** (gap virtualizado + verify compose) |

Código turno: `orchestrator._resolve_list_window_context`, `_collect_treeitem_findall`,
`uia_tree_cache` chain, timeout list 45 s typed roles.

## Cambio propuesto (pseudodiff)

```python
# uia_backend.py — post FindAll gap detection

_FINDALL_GAP_THRESHOLD = 2

def _collect_typed_role_elements(...):
    if role_lower == "treeitem":
        findall_items = self._collect_treeitem_findall(window, cap)
        if findall_items:
            self._last_collect_path = "findall"
            desc_items = self._collect_treeitem_descendants_spotcheck(window, cap)
            if desc_items and len(desc_items) - len(findall_items) >= _FINDALL_GAP_THRESHOLD:
                self._virtualized_gap = len(desc_items) - len(findall_items)
                if self._enumerate_all_requested:
                    return _dedupe_runtime_id(findall_items + desc_items)
            return findall_items
        ...
```

```python
# orchestrator.py — JSON diagnóstico

return {
    ...
    "findall_count": getattr(b, "last_findall_count", None),
    "enumeration_count": len(scoped_elements),
    "virtualized_gap": getattr(b, "virtualized_gap", 0) or 0,
    "collect_path": getattr(b, "last_collect_path", None),
}
```

```python
# list_elements — parámetro opcional

def list_elements(..., enumerate_all: bool = False):
    ...
    # propagate to backend; default false preserves 538 ms fast path
```

## Verificación de duplicados

| Propuesta | Relación |
|-----------|----------|
| 214000 sidebar discovery | **Detección vacía resuelta** — archivar `aplicada`; este ítem cubre **conteo parcial** post-fix |
| 223200 cache miss + collect_path | **Parcial aplicada** — clave orchestrator resuelta; telemetría `collect_path` sigue pendiente en 223200 |
| 222700 / 214500 cold perf | **Cerrar** tras 538 ms — merge archive tema `list-elements-treeitem-perf` |
| 213301 teams_perfect gate | **Extender** fila TE-02: latencia OK; count virtualizado ≠ blocker si find target OK |

**Acción mantenedor:** archivar 214000, 222700, 214500; marcar 223200 parcial
(cache key aplicada); merge telemetría restante con este archivo si se implementa
`collect_path` + `virtualized_gap`.

## Test de abstracción (L4)

Listas virtualizadas Electron/Chromium (Teams, Slack, VS Code tree): fast
enumerate vs completeness — sin IDs de producto en código genérico.

## Esfuerzo observado

Cold perf y cache resueltos en turno; WARN 16 vs 23 bloquea cierre honesto
`teams_perfect` y confunde agente sobre cobertura del rail.

## Criterio de aceptación

- [ ] `tests/test_treeitem_findall_virtualized_gap.py`: mock FindAll=16,
  descendants=23 → `virtualized_gap=7`, default response count=16, `enumerate_all=true` → ≥23.
- [ ] Live Teams: cold p95 < 2000 ms sin `enumerate_all`; target `menur*` findable
  aunque no esté en los 16 visibles.
- [ ] JSON incluye `findall_count`, `virtualized_gap`, `collect_path`.
- [ ] `MCP_TOOLS_REFERENCE.md` documenta trade-off fast vs complete.
- [ ] Skill gate TE-02 (213301) actualizada: no exigir count total chats.
- [ ] Sin regresión cache 0 ms repeat ni leak Cursor en scope.

## Beneficios futuros

- Harness distingue perf OK vs gap virtualización documentado.
- Agente no reintenta paths lentos (12 s) buscando 23 items cuando 16 + find basta.
- Base para scroll-realize en sidebars virtualizados cross-app.

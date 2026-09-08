# list_elements TreeItem: fast paths sin cache + prefetch key mismatch (repeat 11.8 s)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-06 22:32:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | `detection/backends/uia_backend.py`, `detection/orchestrator.py`, `tools/target_window.py` |
| **Tool afectada** | `list_elements`, `set_target_window` |
| **Tipo de gap** | performance |
| **Nivel** | L4 |
| **Impacto** | alto |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** Tras aplicar narrow pane → comtypes spatial → sidebar roots + prefetch async en
`set_target_window`, TE-02 live sigue en **12058 ms** cold y la **segunda** `list_elements(role=TreeItem)`
en la misma sesión tarda **11821 ms** con `backend_used=uia` (no `cache`). Gate `teams_perfect`
exige **< 2000 ms** p95. Detección OK (23 `menur*` sin leak Cursor).

**Causa raíz (código actual):**

1. Los fast paths TreeItem (`_collect_treeitem_from_narrow_panes`, `_collect_treeitem_comtypes_spatial`,
   `_collect_treeitem_via_sidebar_roots`) **retornan antes** de `uia_tree_cache.get_descendants` — solo el
   fallback `_fetch_full_window` usa cache por HWND (`scope=typed:treeitem:{cap}`).
2. Si el path lento es sidebar roots (~10–12 s) y devuelve ≥ 5 items, **cada invocación repite el walk**
   aunque el orchestrator debería cachear — la segunda llamada indica **miss** de `_tree_cache` (clave
   distinta o prefetch no alineado).
3. `_prefetch_electron_treeitem_cache` llama `list_elements(max_depth=6)` fijo; TE-02 agentico usa
   `max_depth=0` → `resolve_list_depth` → clave distinta en `_tree_cache`
   (`{title}|{hwnd}|{depth}|{role}|…`).
4. Sin telemetría `collect_path` / `cache_hit` en JSON no se distingue path lento vs miss de cache en vivo.

**Solución:**

1. Envolver **cada** path TreeItem con `uia_tree_cache.get_descendants` y scopes distintos:
   `treeitem:narrow:{cap}`, `treeitem:spatial:{cap}`, `treeitem:sidebar:{cap}`, `treeitem:direct:{cap}`.
2. En `orchestrator.list_elements`, exponer `cache_hit`, `duration_ms`, `collect_path` (propagado desde
   uia_backend).
3. Prefetch: usar **misma** resolución de profundidad que harness TE-02
   (`normalize_tree_depth` + `resolve_list_depth(0, role=TreeItem)`) y mismos flags
   (`include_offscreen=true`, `view_scope` default).
4. Opcional sync warm con budget 2 s en `set_target` si prefetch async no terminó antes de TE-02.
5. Reordenar fallback si spatial falla: `window.descendants(TreeItem, depth=cap)` **antes** de
   `descendants(Tree, depth=5)` (paridad turno 1182 ms — ver 222700).
6. Tests: cache hit segunda llamada idéntica < 100 ms; mock sidebar lento invocado una sola vez.

**Dónde:** `uia_backend.py` (`_collect_typed_role_elements`), `orchestrator.py`, `target_window.py`,
`docs/MCP_TOOLS_REFERENCE.md` § list_elements.

## Contexto del turno

| Métrica | Turno anterior (sidebar roots) | Turno actual (spatial + prefetch) |
|---------|-------------------------------|-----------------------------------|
| `list_elements(TreeItem)` cold | 12924 ms | **12058 ms** SLOW |
| Segunda list misma sesión | 0 ms (cache hit reportado) | **11821 ms** uia, no cache |
| TreeItem count | 23 | **23** menur* |
| TE-08 scroll | — | Scroll.Scroll up/down OK |
| TE-08 find_text post-scroll | — | texto ausente tras scroll up |
| pytest target+perf | 19 passed | **31 passed** |
| teams_perfect | false | **false** |

Código aplicado: `_walk_treeitems_spatial_pruned`, `_collect_treeitem_from_narrow_panes`,
`_collect_treeitem_comtypes_spatial`, orden narrow→spatial→sidebar→cached full;
`_prefetch_electron_treeitem_cache` thread en `set_target` Electron.

## Cambio propuesto (pseudodiff)

```python
# uia_backend.py — cache en todos los paths TreeItem

def _cached_treeitem_collect(hwnd: int, scope: str, cap: int, fetch: Callable) -> list:
    from detection.uia_tree_cache import get_descendants
    return get_descendants(hwnd, fetch, scope=f"treeitem:{scope}:{cap}", ttl_s=30.0)

def _collect_typed_role_elements(...):
    if role_lower == "treeitem":
        hwnd = self._window_hwnd(window)
        paths = [
            ("narrow", lambda: self._collect_treeitem_from_narrow_panes(window, cap)),
            ("spatial", lambda: self._collect_treeitem_comtypes_spatial(window, cap)),
            ("direct", lambda: window.descendants(control_type="TreeItem", depth=cap)),
            ("sidebar", lambda: self._collect_treeitem_via_sidebar_roots(window, cap)),
        ]
        for name, fn in paths:
            items = _cached_treeitem_collect(hwnd, name, cap, fn) if hwnd else fn()
            if len(items) >= _SIDEBAR_TREE_MIN_ITEMS:
                self._last_collect_path = name  # propagar a JSON
                return items
        ...
```

```python
# target_window.py — prefetch alineado con TE-02

def _prefetch_electron_treeitem_cache(...):
    from detection.tree_depth import normalize_tree_depth, resolve_list_depth
    md = normalize_tree_depth(0)
    _, md, _ = resolve_list_depth(md, window_title=title, role="TreeItem")
    get_orchestrator().list_elements(
        window_title=title, max_depth=md, role="TreeItem",
        window_handle=hwnd or None, include_offscreen=True,
    )
```

```python
# orchestrator.py — respuesta diagnóstica

return {
    ...,
    "duration_ms": elapsed_ms,
    "cache_hit": from_cache,
    "collect_path": getattr(backend, "last_collect_path", None),
}
```

## Verificación de duplicados

| Propuesta | Relación |
|-----------|----------|
| 214500 list TreeItem perf uia-first | **Consolidar** — fast path direct enumerate; mantenedor archivar tras merge |
| 222700 comtypes spatial live fix | **Extender** — mismo tema cold 12 s; este ítem cubre **cache miss repeat** + telemetría |
| 213301 teams_perfect gate | Vigente — fila TE-02 latency |
| 213300 scroll keyboard | Distinto — TE-08 scroll nativo ya OK este turno |

**Acción mantenedor:** merge 214500 + 222700 + este archivo en una spec única tema `list-elements-treeitem-perf`.

## Test de abstracción (L4)

Electron/Chromium con nav rail estrecho: Slack, Discord, VS Code — cache por HWND+scope sin IDs Teams.

## Esfuerzo observado

Dos listas consecutivas ~12 s bloquean harness agentico; prefetch no amortiza TE-02; find 633 ms vs list 12 s
confirma gap en collect/cache, no routing agente.

## Criterio de aceptación

- [ ] `tests/test_treeitem_cache_paths.py`: segunda `list_elements` idéntica → `cache_hit=true`, < 100 ms.
- [ ] Mock path sidebar: primera invocación lenta, segunda sin re-ejecutar fetch (uia_tree_cache u orchestrator).
- [ ] Prefetch usa `resolve_list_depth` — misma clave que TE-02 harness.
- [ ] Live Teams: cold < 2000 ms p95 **o** warm segunda llamada < 100 ms con `collect_path` estable.
- [ ] JSON incluye `collect_path`, `duration_ms`, `cache_hit`.
- [ ] Sin regresión scope 23 chats / 0 leak Cursor.
- [ ] Documentado en `MCP_TOOLS_REFERENCE.md`.

## Beneficios futuros

- Repeticiones TE-02/TE-05/TE-10 no pagan 12 s por observación.
- Prefetch en `set_target` amortiza discovery real del harness.
- Telemetría permite cerrar blockers sin adivinar path UIA en vivo.

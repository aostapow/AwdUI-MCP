# list_elements: comtypes spatial TreeItem live fix + fallback order (cold 12–13 s)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-06 22:27:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | `detection/backends/uia_backend.py`, `tools/target_window.py`, `detection/orchestrator.py` |
| **Tool afectada** | `list_elements`, `set_target_window` |
| **Tipo de gap** | performance |
| **Nivel** | L4 |
| **Impacto** | alto |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** Tras wiring de `_collect_treeitem_via_sidebar_roots`, `uia_tree_cache` (TTL 30 s) y
orchestrator `_CACHE_TTL` 20 s, TE-02 devuelve **23 TreeItems** sin leak `list_id_*` (detección OK),
pero el cold path sigue en **12374–12924 ms SLOW** (gate `teams_perfect`: < **2000 ms**). Cache repeat
**0 ms**. `find_element` menur* **633 ms** OK; `invoke_element` TE-05 **979–1642 ms** OK.

**Causa raíz (fallback chain regresiva):**

1. `_collect_typed_role_elements` intenta primero `_collect_treeitem_comtypes_spatial` (walk comtypes
   con `prune_left_abs`); en Teams live devuelve **< 5 items** → se considera fallo.
2. Fallback `_collect_treeitem_via_sidebar_roots` ejecuta `window.descendants(control_type="Tree",
   depth=5)` sobre **toda** la ventana TeamsWebView → recorre WebView masivo (~10–13 s).
3. Turno previo con solo `window.descendants(TreeItem)` directo + skip spy alcanzó **1182 ms**; el
   nuevo fallback sidebar empeora el cold path aunque mejora cobertura offscreen.
4. `uia_tree_cache` solo amortiza repeticiones idénticas; no ayuda al primer `list_elements` agentico
   post `set_target_window` (TE-02).

**Solución:**

1. **Arreglar spatial live:** instrumentar y corregir `_walk_treeitems_spatial_pruned` /
   `_window_prune_left_abs` para TeamsWebView (depth cap, `prune_left` con banda 120–520 px,
   `ControlViewWalker` vs `RawViewWalker` si TreeItems solo en raw). Objetivo: ≥ 5 TreeItems en
   **< 1500 ms** sin full-window `descendants(Tree)`.
2. **Reordenar fallback (nunca full-window Tree scan antes de direct enumerate):**
   - spatial comtypes → `window.descendants(TreeItem, depth=cap)` (paridad turno 1182 ms) →
     sidebar Tree roots **solo** si direct enumerate vacío.
3. **Warm cache en `set_target_window`:** tras resolver HWND target en Electron/Chromium, prefetch
   `uia_tree_cache` scope `typed:treeitem:{cap}` en thread daemon o sync con budget 2 s; TE-02 cold
   debe ser cache hit.
4. **JSON diagnóstico:** `collect_path` ∈ `spatial_comtypes|direct_treeitem|sidebar_tree_roots|full_window`,
   `duration_ms`, `treeitem_count`, `prune_left_abs`.
5. Tests: `tests/test_treeitem_comtypes_spatial.py` con mock bbox sidebar + WebView ancho; live gate
   TE-02 cold < 2000 ms.

**Dónde:** `uia_backend.py` (`_collect_typed_role_elements`, `_walk_treeitems_spatial_pruned`),
`target_window.py` (warm prefetch hook), `docs/MCP_TOOLS_REFERENCE.md` § list_elements.

## Contexto del turno

| Métrica | Turno previo (214500 aplicado) | Turno actual (sidebar roots) |
|---------|--------------------------------|------------------------------|
| `list_elements(role=TreeItem)` cold | **1182 ms** OK | **12374–12924 ms** SLOW |
| Cache repeat | — | **0 ms** |
| TreeItem count | 23 | **23** (sin `list_id_*` leak) |
| `find_element` menur1r | 639 ms | **633 ms** OK |
| `invoke_element` TE-05 | 19–21 s (falso SLOW) | **979–1642 ms** OK |
| pytest perf+scope | 19 passed | **19 passed** |
| teams_perfect | false | **false** (cold list) |

Código turno: `_collect_treeitem_via_sidebar_roots` (Tree width 120–520), `uia_tree_cache` on typed
fetch, orchestrator `_CACHE_TTL` 20 s, revert progressive depth TreeItem.

## Cambio propuesto (pseudodiff)

```python
# uia_backend.py — _collect_typed_role_elements (treeitem branch)

if role_lower == "treeitem":
    spatial = self._collect_treeitem_comtypes_spatial(window, cap)
    if len(spatial) >= _SIDEBAR_TREE_MIN_ITEMS:
        return spatial

    # Fast direct enumerate BEFORE expensive Tree-root scan
    direct = _fetch_treeitems_direct(window, control_type, cap)
    if len(direct) >= _SIDEBAR_TREE_MIN_ITEMS:
        return direct

    sidebar = self._collect_treeitem_via_sidebar_roots(window, cap)
    if sidebar:
        return sidebar
    # ... uia_tree_cache + full window last resort
```

```python
# target_window.py — after successful set_target

def _maybe_warm_treeitem_cache(hwnd: int, window_title: str) -> None:
    from detection.backends.uia_backend import _prefer_uia_find_before_spy
    from tools.framework_detect import do_detect_framework
    fw = do_detect_framework(window_title).get("framework", "")
    if fw not in ("electron", "chromium_browser", "chromium_embedded"):
        return
    if not _prefer_uia_find_before_spy(window_title):
        return
    # prefetch typed:treeitem:6 with 2s budget; ignore errors
    ...
```

```python
# _walk_treeitems_spatial_pruned — fix prune for nested WebView

def walk(elem, depth: int) -> None:
    if depth > max_depth:
        return
    left = _element_rect_left(elem)
    ct = _element_control_type(elem)
    # Do not prune Document/WebView containers at shallow depth
    if depth >= 3 and ct not in (_UIA_DOCUMENT, _UIA_PANE) and left > prune_left_abs:
        return
    ...
```

## Verificación de duplicados

| Propuesta | Relación |
|-----------|----------|
| 214000 list TreeItem vacío | **Detección resuelta** — archivar `aplicada`; no reabrir |
| 214500 list TreeItem perf uia-first | **Parcialmente aplicada** — 1182 ms logrado; regresión cold con sidebar fallback; **extender con este ítem**, no duplicar spec fast path |
| 214800 invoke probe timing | **Resuelto** — invoke 979–1642 ms; archivar `aplicada` |
| 213301 teams_perfect gate | Vigente — este fix cierra fila TE-02 latency del gate |
| 213300 scroll keyboard | P2 distinto — TE-08 ya met con Scroll nativo |
| 180100 discovery wall-clock | `discover_target` — no `list_elements` |

Consolidación tema `list-elements` + `performance`: **una** spec unificada (este archivo + cerrar 214500).

## Test de abstracción (L4)

Cross-app: Electron/Chromium con nav rail estrecho + content WebView ancho (Slack, Discord, VS Code).
Sin IDs Teams en servidor; heurística bbox + warm cache por HWND.

## Esfuerzo observado

TE-02 discovery funcional pero SLOW bloquea `teams_perfect`; agente no puede cumplir gate eficiencia
sin waiver; find 633 ms vs list 12 s demuestra gap en cadena collect, no routing agente.

## Criterio de aceptación

- [ ] `tests/test_treeitem_comtypes_spatial.py`: mock sidebar 23 TreeItems + WebView ancho → spatial
      path ≥ 5 items, sidebar_roots **no** invocado.
- [ ] Fallback order test: spatial vacío → direct TreeItem antes de `descendants(Tree)`.
- [ ] Live Teams TE-02: `list_elements(role=TreeItem)` cold **< 2000 ms**, count ≥ 1, `collect_path`
      ≠ `sidebar_tree_roots` en p95.
- [ ] Post `set_target_window`: segunda llamada idéntica < 100 ms (cache hit).
- [ ] Sin regresión scope: 0 leak Cursor/`list_id_*`; count ~20–30 chats.
- [ ] Documentado en `MCP_TOOLS_REFERENCE.md` § list_elements (`collect_path`, warm cache).
- [ ] `state.json` blocker cold list removable; `teams_perfect` re-eval con gate 213301.

## Beneficios futuros

- Restaura latencia ~1 s del turno 214500 sin perder cobertura 23 chats del sidebar roots.
- Cold TE-02 usable en harness agentico sin waiver de eficiencia.
- Warm cache en set_target amortiza discovery en toda sesión Teams/Electron.

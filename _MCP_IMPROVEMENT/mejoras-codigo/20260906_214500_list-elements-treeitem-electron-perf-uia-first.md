# list_elements: TreeItem Electron post-scope fix — latencia 5637 ms (paridad find 523 ms)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-06 21:45:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | `detection/orchestrator.py`, `detection/backends/uia_backend.py`, `tools/ui_automation.py` |
| **Tool afectada** | `list_elements` |
| **Tipo de gap** | performance |
| **Nivel** | L4 |
| **Impacto** | alto |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** Tras fix `element_scope` (`allow_renderer_pid` + `_drop_electron_compact_tree_rows`) y
`include_offscreen=true` default para TreeItem/ListItem/TabItem, TE-02 regression devuelve **23 chats**
(incl. `menur1oc` Awamori) sin leak Cursor — pero `list_elements(role=TreeItem, view_scope=true)` tarda
**5637 ms SLOW** (umbral gate `teams_perfect`: < **2000 ms**). `find_element` mismo chat **523 ms**.

**Causa raíz (asimetría find/list post-detección):**

1. `find_element` en Electron ya usa `_find_raw_direct` / UIA-first con skip spy sidecar.
2. `list_elements` sigue recorriendo árbol completo con `include_offscreen=true` (más nodos) y puede
   invocar merge spy FlaUI antes de scope filter — costo ~5× vs find puntual.
3. Cache `_tree_cache` ayuda en repeticiones idénticas, pero TE-02 discovery es cold path agentico.
4. `view_scope=true` no acelera el walk; solo filtra post-collect.

**Solución:** Fast path enumerate para roles sidebar en Electron (paridad con find perf 204701):

1. **`_list_role_fast_path`** en `uia_backend.list_elements`: si `role=TreeItem|ListItem` +
   framework ∈ (`electron`, `chromium_browser`) → `window.descendants(control_type=role, depth≤24)`
   sin spy merge; retorno temprano si `count ≥ 1`.
2. **Skip spy** en orchestrator cuando `_prefer_uia_find_before_spy(window_title)` — misma regla que
   find; JSON `spy_skipped: true`, `uia_backend: "direct_enumerate"`.
3. **`view_scope` + TreeItem:** auto-off implícito o walk root = ventana completa (nav rail) — evita
   doble walk content pane + sidebar (complementa 204701 aplicada en find).
4. Respuesta JSON: `duration_ms`, `fast_path`, `include_offscreen_effective`, `treeitem_count`.
5. Objetivo live TE-02: **< 2000 ms** p95 con count ≥ 1.

**Dónde:** `uia_backend.py`, `orchestrator.list_elements`, `docs/MCP_TOOLS_REFERENCE.md`;
tests `tests/test_list_elements_treeitem_electron_perf.py`.

## Contexto del turno

| Métrica | Antes (214000) | Después (element_scope fix) |
|---------|----------------|----------------------------|
| `list_elements(role=TreeItem)` | vacío / leak 48 `list_id_*` | **23 chats** OK incl. Awamori |
| `list_elements` latency | N/A (vacío) | **5637 ms SLOW** |
| `find_element` menur1oc | 786 ms (prior turn) | **523 ms** OK |
| `scroll_element` message pane | ScrollPattern N/A | `scroll_fallback_coords` OK (P2) |
| pytest | — | **832 passed**, 1 fail unrelated |
| teams_matrix | 21/21 met | 21/21 met |
| teams_perfect | false | **false** (latency + scroll) |

Fix turno: `element_scope.py` `allow_renderer_pid`; `_drop_electron_compact_tree_rows` height<28;
orchestrator `include_offscreen=true` treeitem/listitem/tabitem; `test_element_scope.py` reparado.

## Cambio propuesto (pseudodiff)

```python
# uia_backend.py

_SIDEBAR_ROLES = frozenset({"treeitem", "listitem"})

def _collect_sidebar_role_fast(
    window, role_lower: str, max_depth: int, include_offscreen: bool
) -> list[DetectedElement]:
    ctype = role_lower.capitalize()  # TreeItem, ListItem
    out = []
    for desc in window.descendants(control_type=ctype, depth=min(max_depth, 24)):
        d = _pywinauto_to_element(desc)
        if d and (include_offscreen or d.visible):
            out.append(d)
    return out

def list_elements(..., role=None, view_scope=False, ...):
    role_lower = (role or "").strip().lower()
    fw = do_detect_framework(window_title).get("framework", "")
    uia_first = _prefer_uia_find_before_spy(window_title)

    if role_lower in _SIDEBAR_ROLES and fw in ("electron", "chromium_browser") and uia_first:
        fast = _collect_sidebar_role_fast(window, role_lower, max_depth, include_offscreen)
        if fast:
            return {
                "elements": fast,
                "fast_path": "direct_enumerate",
                "spy_skipped": True,
            }
    # existing walk + optional spy (skip spy if uia_first)
    ...
```

```python
# orchestrator.py — after successful fast path from uia backend
if result.get("fast_path"):
    scoped, scoped_out, cluster_out, region = filter_elements_to_scope(
        result["elements"], window_title, adaptive_cluster=adaptive_cluster
    )
    return {..., "duration_ms": elapsed, "fast_path": result["fast_path"]}
```

**Uso agente TE-02 post-fix:**
```
list_elements(role="TreeItem", max_depth=12, view_scope=true)
# Objetivo: count ≥ 1, duration_ms < 2000, spy_skipped=true
```

## Verificación de duplicados

- **Extiende** `20260906_214000` — detección vacío resuelta por `element_scope` este turno; **este ítem
  cubre latencia residual**, no re-abrir detección. Mantenedor: archivar 214000 como `aplicada` (parcial)
  tras validar perf.
- **Complementa** `20260906_204701` (view_scope find perf, aplicada) — paridad list/find enumerate.
- **No duplica** `20260906_213300` (scroll keyboard) — distinto concern P2 scroll.
- **No duplica** `20260906_213301` (teams_perfect gate skill) — este fix cierra fila latency del gate.
- Consolidación tema `list-elements` + `performance`: una spec perf unificada vs re-propuesta detección.

## Test de abstracción (L4)

Cross-app: Slack/Discord/VS Code sidebar TreeItem virtualizados; cualquier Electron con nav rail +
`allow_renderer_pid` scope — sin IDs Teams en servidor.

## Esfuerzo observado

TE-02 regression OK funcional pero SLOW bloquea `teams_perfect`; agente repite discovery cold path;
find 523 ms vs list 5637 ms demuestra gap servidor, no routing agente.

## Criterio de aceptación

- [ ] `tests/test_list_elements_treeitem_electron_perf.py`: mock 23 TreeItems → `duration_ms` < 2000
      (sin spy sidecar mock).
- [ ] Live Teams TE-02: `list_elements(role=TreeItem", view_scope=true)` ≥ 1 item, **< 2000 ms**,
      `fast_path=direct_enumerate`.
- [ ] Sin regresión scope: 0 leak Cursor/`list_id_*`; count estable ~20–30 chats.
- [ ] Cache hit segunda invocación idéntica < 100 ms.
- [ ] Documentado en `MCP_TOOLS_REFERENCE.md` § list_elements (fast path sidebar roles + metrics JSON).
- [ ] `state.json` blocker latency TE-02 removible tras live verify; `teams_perfect` eval con 213301 gate.

## Beneficios futuros

- Cierra blocker P1 latency post-fix detección TreeItem para `teams_perfect`.
- Paridad find/list reutilizable en sidebars Electron virtualizados.
- Reduce costo agentico OBS fase 3 en harness Teams y apps similares.

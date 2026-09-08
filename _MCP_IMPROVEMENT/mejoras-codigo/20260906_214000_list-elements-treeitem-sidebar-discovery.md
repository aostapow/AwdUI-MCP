# list_elements: TreeItem vacío en sidebar Electron (find OK, list vacío)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-06 21:40:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | `detection/backends/uia_backend.py`, `detection/orchestrator.py`, `tools/ui_automation.py` |
| **Tool afectada** | `list_elements`, `find_element` |
| **Tipo de gap** | deteccion |
| **Nivel** | L4 |
| **Impacto** | medio |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** Tras el ciclo find perf Teams (UIA-first, `child_window` directo, depth ladder
6–24, `view_scope`, `adaptive_cluster=false` para TreeItem), `find_element(name~="Awamori",
role="TreeItem")` responde en **~786 ms** (antes ~10 s). En cambio `list_elements(role="TreeItem")`
sigue devolviendo **lista vacía** en TE-02 discovery y en verify post-fix — bloqueador P2 en
`state.json` junto a scroll N/A.

**Causa raíz (asimetría find vs list):**

1. `find_elements` en Electron usa `_find_raw_direct` (`child_window` + `title_re`) **antes** del
   walk; `list_elements` solo hace `_collect_descendants` + spy merge sin lookup dirigido.
2. TreeItems del chat sidebar viven en nav rail estrecho; `view_scope=true` (204701) restringe
   walk al content pane ancho → **excluye** sidebar donde están los TreeItem.
3. `include_offscreen=false` (default) puede filtrar TreeItems virtualizados fuera de viewport.
4. `list_elements` aún invoca spy FlaUI en Electron aunque `find` ya prioriza UIA-first — walk
   lento y a veces vacío para roles de lista virtualizada.

**Solución:** Paridad find/list para roles de sidebar en frameworks Electron/Chromium:

1. **`view_scope` auto-off** cuando `role ∈ {TreeItem, ListItem}` y no hay `view_scope` explícito
   del agente — o resolver walk root = nav rail band (heurística bbox estrecha izquierda, genérica).
2. **`_list_role_fast_path`**: para `role=TreeItem` + electron, intentar
   `window.descendants(control_type="TreeItem", depth=24)` y/o localizar contenedor `Tree`/`List`
   por UIA antes del walk comtypes completo; reutilizar lógica de `_find_raw_direct` en modo
   enumerate (sin `name`).
3. **`include_offscreen` default inteligente**: si `role=TreeItem|ListItem` y framework electron →
   default `include_offscreen=true` salvo override explícito.
4. **Skip spy en `list_elements`** cuando `_prefer_uia_find_before_spy(window_title)` (misma regla
   que find) — respuesta incluye `spy_skipped: true`, `uia_backend: "direct"`.
5. Respuesta JSON: `sidebar_walk_root`, `treeitem_count`, `view_scope_applied`, `include_offscreen_effective`.

**Dónde:** `uia_backend.list_elements`, `orchestrator.list_elements`, `spatial_cluster.py`
(opcional nav-rail root), `docs/MCP_TOOLS_REFERENCE.md`; tests
`tests/test_list_elements_treeitem_electron.py`.

## Contexto del turno

| Métrica | Antes | Después (turno find perf) |
|---------|-------|---------------------------|
| `find_element` TreeItem Awamori | ~10 s SLOW | **786 ms** OK |
| `find_element` por automation_id | — | **337 ms** OK |
| `list_elements(role=TreeItem)` | vacío / TE-02 discovery falla | **sigue vacío** (blocker) |
| Verify post-act TreeItem | ~12 s | early pass estable (title re-select) |
| pytest | — | **27+ passed** |
| 204701 view_scope | propuesta | **aplicada** (archivada) |

Blockers residuales `state.json`: scroll N/A (213300 vigente); list_elements TreeItem (este ítem).

## Cambio propuesto (pseudodiff)

```python
# uia_backend.py — list_elements

_SIDEBAR_ROLES = frozenset({"treeitem", "listitem"})

def _resolve_sidebar_walk_root(window, role_lower: str, view_scope: bool):
    if view_scope and role_lower in _SIDEBAR_ROLES:
        return window  # nav rail, not content pane
    if view_scope:
        return resolve_content_walk_root(window) or window
    return window

def _collect_treeitems_fast(window, max_depth: int, include_offscreen: bool) -> list:
    items = []
    try:
        for desc in window.descendants(control_type="TreeItem", depth=min(max_depth, 24)):
            d = _pywinauto_to_element(desc)
            if d and (include_offscreen or d.visible):
                items.append(d)
    except Exception:
        pass
    return items

def list_elements(..., view_scope: bool = False, include_offscreen: bool = False, role: Optional[str] = None):
    role_lower = (role or "").strip().lower()
    uia_first = _prefer_uia_find_before_spy(window_title)
    if role_lower in _SIDEBAR_ROLES and not include_offscreen:
        fw = do_detect_framework(window_title).get("framework", "")
        if fw in ("electron", "chromium_browser"):
            include_offscreen = True  # document in response

    walk_root = _resolve_sidebar_walk_root(window, role_lower, view_scope)

    if role_lower == "treeitem" and uia_first:
        fast = _collect_treeitems_fast(walk_root, max_depth, include_offscreen)
        if fast:
            return dedupe_detected_elements(fast)

    # existing _collect_descendants + spy (skip if uia_first)
    skip_spy = uia_first or (role_lower in ("menuitem", "menu") and bool(elements))
    ...
```

**Uso agente TE-02:**
```
list_elements(role="TreeItem", max_depth=12, view_scope=false)
# Objetivo: count ≥ 1, incluye Awamori; duration_ms < 2000
```

## Verificación de duplicados

- **Extiende** `20260906_204701` (view_scope) — no contradice; auto-off TreeItem evita excluir nav rail.
- **Complementa** `tests/test_uia_find_performance.py` — find fast path ya cubierto; falta paridad list.
- **No duplica** `20260906_213300` (scroll keyboard) — distinto concern.
- **No duplica** skills TE-05/09 (`203630`, `204500`) — documentan flujo agente; este gap es servidor.
- Consolidación: marcar `20260906_212500` como aplicada tras verify ~426 ms estable (mantenedor archive).

## Test de abstracción (L4)

Cross-app: Slack/Discord/VS Code activity sidebar con TreeItem/ListItem virtualizados; cualquier
Electron con nav rail + content pane — sin IDs Teams en servidor.

## Esfuerzo observado

TE-02 discovery bloqueado; agente depende de `find_element(name=…)` puntual mientras inventario
TreeItem para mapeo inicial falla. Asimetría find 786 ms vs list vacío impide OBS fase 3 genérica.

## Criterio de aceptación

- [ ] `tests/test_list_elements_treeitem_electron.py`: mock sidebar TreeItems offscreen →
      `list_elements(role=TreeItem)` count ≥ 1 con `include_offscreen_effective=true`.
- [ ] `view_scope=true` + `role=TreeItem` no excluye nav rail (auto-off o nav root).
- [ ] Live Teams TE-02: `list_elements(role=TreeItem", max_depth=12)` ≥ 1 item, < **2000 ms**.
- [ ] `list_elements` en electron incluye `spy_skipped: true` cuando UIA-first.
- [ ] Sin regresión `view_scope` Button inventory TE-10 (< 2 s, count < 35).
- [ ] Documentado en `MCP_TOOLS_REFERENCE.md` § list_elements (sidebar roles + view_scope interaction).

## Beneficios futuros

- TE-02 discovery programático sin depender solo de `find_element` con name.
- Cierra blocker P2 list TreeItem para evaluación `teams_perfect`.
- Paridad find/list reutilizable en apps Electron con sidebars virtualizados.

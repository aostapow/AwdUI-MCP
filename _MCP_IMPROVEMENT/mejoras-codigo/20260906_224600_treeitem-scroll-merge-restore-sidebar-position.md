# list_elements TreeItem: restaurar scroll sidebar post scroll-merge

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-06 22:46:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | `detection/backends/uia_backend.py`, `detection/uia_patterns.py` |
| **Tool afectada** | `list_elements`, `invoke_element`, `scroll_into_view` |
| **Tipo de gap** | deteccion |
| **Nivel** | L4 |
| **Impacto** | alto |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** Tras implementar `_collect_treeitem_findall` scroll-merge (SetScrollPercent
100/0 + loop ScrollPattern + keyboard nudge), TE-02 cold lista **49** TreeItems offscreen
(Reyes `menur31`) en **3398 ms** — gap de virtualización resuelto. Pero el sidebar queda
**scrolleado** al final del sweep; el paso siguiente TE-03 `invoke_element(menur1r)`
falla **12783 ms** SLOW (stale / item fuera de viewport) aunque el chat Awamori sigue
activo en header (OCR+screenshot OK). `teams_perfect` permanece `false`.

**Causa raíz:** `_collect_treeitem_findall` no restaura posición de scroll tras
materializar filas virtualizadas. El agente asume que `list_elements` es observación
no destructiva; el scroll-merge muta estado UI visible y rompe re-selección de chats
ya abiertos en la parte superior de la lista.

**Solución:**

1. Guardar `vertical_percent` inicial vía `ScrollPattern` (o ancla: primer TreeItem
   visible `automation_id` + `y`) antes del sweep.
2. Tras merge final, **restaurar** scroll:
   - `apply_scroll_pattern(..., vertical_percent=0.0)` (Home/top), o
   - `SetScrollPercent` al valor guardado, o
   - `scroll_into_view` del TreeItem con `SelectionItem.IsSelected=true` si existe.
3. Flag JSON opcional: `sidebar_scroll_mutated: true`, `sidebar_scroll_restored: true`.
4. Si restore falla, incluir `restore_warning` para que el agente invoque
   `scroll_into_view(automation_id=menur*)` antes de `invoke_element`.
5. Tests mock: sweep down → restore → `invoke` mock no requiere 12 s re-walk.

**Dónde:** `uia_backend._collect_treeitem_findall` (bloque `finally` o trailing
restore); `docs/MCP_TOOLS_REFERENCE.md` § list_elements TreeItem scroll-merge;
skill `teams/element-map.md` nota WARN sidebar scrolleado.

## Contexto del turno

| Métrica | Turno 5 (FindAll 16) | Turno 6 (scroll-merge) |
|---------|---------------------|------------------------|
| `list_elements(TreeItem)` cold | 578 ms, 16 items | **3398 ms**, **49** items |
| Cache repeat | 0 ms | **0 ms** |
| Offscreen Reyes menur31 | find 888 ms workaround | **en lista** |
| TE-03 nav rail | — | Calendario/Llamadas/Chat OK |
| `invoke_element(menur1r)` post-list | — | **12783 ms FAIL** SLOW |
| Keyboard nudge Start menu | — | Abierto antes de `ensure_focus` fix |
| pytest | 15 passed | **16 passed** |
| teams_perfect | false (16 vs 23) | **false** (cold SLOW + sidebar state) |

Código turno: `_collect_treeitem_findall`, `_sidebar_keyboard_nudge`,
`ensure_focus_for_input` antes de nudge, `_resolve_sidebar_scroll_raw`,
`_merge_treeitem_wrappers`.

## Cambio propuesto (pseudodiff)

```python
# uia_backend.py — restore after scroll-merge

def _collect_treeitem_findall(self, window, cap: int) -> list:
    ...
    scroll_raw = self._resolve_sidebar_scroll_raw(merged)
    initial_vpct = self._read_vertical_scroll_percent(scroll_raw) if scroll_raw else None
    selected_anchor = self._find_selected_treeitem_automation_id(merged)

    try:
        # existing SetScrollPercent 100/0, loop, keyboard nudge ...
        ...
        return merged
    finally:
        if scroll_raw is not None:
            if selected_anchor:
                self._scroll_treeitem_into_view(window, selected_anchor)
            elif initial_vpct is not None:
                apply_scroll_pattern(scroll_raw, vertical_percent=initial_vpct)
            else:
                apply_scroll_pattern(scroll_raw, direction="up", vertical_percent=0.0)
            self._sidebar_scroll_restored = True
```

```python
# orchestrator.py — telemetría

return {
    ...,
    "sidebar_scroll_mutated": getattr(backend, "sidebar_scroll_mutated", False),
    "sidebar_scroll_restored": getattr(backend, "sidebar_scroll_restored", False),
}
```

## Verificación de duplicados

| Propuesta | Relación |
|-----------|----------|
| 223500 virtualized gap 16 vs 23 | **Resuelto** por scroll-merge — archivar `aplicada`; este ítem cubre **efecto lateral** |
| 223201 TE-08 scroll verify | Distinto — message pane, no sidebar chat list |
| 204500 TE-09 return chat scroll | Skill workaround; este ítem es fix MCP genérico post-list |
| 213301 teams_perfect gate | **Extender** fila TE-03: invoke post-list sin stale |

**Acción mantenedor:** marcar 223500 `aplicada` tras validar restore; no duplicar gap virtualizado.

## Test de abstracción (L4)

Sidebars virtualizados Electron (Teams, Slack, Discord): cualquier `list_elements` que
haga scroll para enumerar debe restaurar viewport — sin IDs de producto en servidor.

## Esfuerzo observado

TE-03 met por OCR fallback pero 12 s en re-select bloquea calidad MCP; fricción visible
en harness agentico post TE-02.

## Criterio de aceptación

- [ ] `tests/test_treeitem_scroll_restore.py`: mock sweep muta scroll → restore llamado;
      `sidebar_scroll_restored=true` en JSON.
- [ ] Live Teams: tras `list_elements(TreeItem)` cold, `invoke_element(menur1r)` < **2000 ms**
      sin OCR workaround.
- [ ] Chat seleccionado visible en sidebar tras list (screenshot o `get_element_bounds` y < viewport).
- [ ] Sin regresión: 49 items cold, cache 0 ms, menur31 presente.
- [ ] Documentado en `MCP_TOOLS_REFERENCE.md` y `teams/element-map.md` (quitar WARN sidebar scrolleado).
- [ ] Gate 213301: fila TE-03 invoke post-discovery < 2000 ms.

## Beneficios futuros

- `list_elements` vuelve a ser observación segura antes de invoke/verify.
- TE-05/TE-10 no pagan re-walk 12 s tras discovery.
- Cierra blocker `teams_perfect` de estado sidebar mutado (complementa perf cold).

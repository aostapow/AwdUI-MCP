# list_elements: view_scope por título ventana (Electron Teams)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | aplicada |
| **Fecha** | 2026-09-06 20:47:01 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | detection/orchestrator.py, detection/backends/uia_backend.py, tools/ui_automation.py, tools/target_window.py |
| **Tool afectada** | list_elements, find_element |
| **Tipo de gap** | performance |
| **Nivel** | L4 |
| **Impacto** | medio |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** En Teams Electron (TE-10 Calendario), `list_elements(role=Button)` devolvió 81
controles en **4637 ms** (⚠ SLOW) pese al filtro de rol. TE-02 registró 450 elementos en
7191 ms con `max_depth=8`. El walk recorre subárboles de nav rail, sidebar chat oculto y
controles offscreen de otras secciones aunque el título de ventana ya indica vista activa
(`Calendar|Microsoft Teams`). El scope por HWND/PID no acota al panel de contenido de la
vista actual.

**Solución:** Parámetro opcional `view_scope: bool = false` (o `content_pane_only: bool`) en
`list_elements` / `find_element`: cuando el título de la ventana objetivo contiene un segmento
de vista conocido (`Calendar`, `Chat`, `General`, etc.), restringir el walk UIA al subárbol del
**main content pane** (heurística genérica: `Document` / `Pane` más ancho dentro del client
rect, excluyendo bandas laterales nav rail ya mapeadas por cluster espacial). Combinar con
`role=` existente. Respuesta incluir `view_scope_applied`, `walk_root_role`,
`elements_before_view_filter`, `duration_ms` desglosado (walk vs filter).

Alternativa agente hasta fix: no invocar `list_elements` en TE-10 verify (skill `204700`).

**Dónde:** `uia_backend.list_elements`, `orchestrator.py`, `spatial_cluster.py` (banda
dominante), `docs/MCP_TOOLS_REFERENCE.md`; tests `tests/test_list_elements_view_scope.py`.

## Contexto del turno

| Métrica | TE-02 discovery | TE-10 calendario |
|---------|-----------------|------------------|
| Tool | `list_elements max_depth=8` | `list_elements role=Button` |
| Count | 450 | 81 |
| Duration | 7191 ms SLOW | 4637 ms SLOW |
| Vista | Teams general | `Calendar\|Microsoft Teams` |

Turno TE-10 met funcional; fricción performance bloquea loops agenticos en TE-11+ si el
agente repite inventario Button en cada sección nav rail.

## Cambio propuesto (pseudodiff)

```python
# ui_automation.py list_elements tool
view_scope: bool = False  # restrict walk to dominant content pane when inferrable

# uia_backend.py
def _resolve_content_pane_root(window_root, window_title: str) -> dict:
    """Generic: widest Pane/Document in client rect excluding narrow left rail band."""
    segments = _title_view_segments(window_title)  # e.g. ["Calendar", "Microsoft Teams"]
    if not segments:
        return window_root
    candidates = walk_shallow(window_root, max_depth=4, roles=("Pane", "Document"))
    return max(candidates, key=lambda c: c["bbox"]["width"], default=window_root)


def list_elements(..., view_scope: bool = False, role: Optional[str] = None):
    root = resolve_window_root(window_title)
    if view_scope:
        root = _resolve_content_pane_root(root, window_title)
    listing = walk_subtree(root, max_depth=max_depth, role=role, ...)
    return {
        "elements": listing,
        "view_scope_applied": view_scope,
        "walk_root": "content_pane" if view_scope else "window",
        ...
    }
```

**Uso agente (TE-10 diagnóstico):**
```
invoke_element(automation_id="ef56c0de")  # Calendario
list_elements(role="Button", view_scope=true, max_depth=6)
# Objetivo: <2 s, <30 Button (toolbar calendario + celdas visibles)
```

## Verificación de duplicados

- **Extiende** `20260905_210301` (`within_automation_id` popup/ancestro) — distinto trigger:
  vista inferida por **título ventana** + geometría, no `automation_id` fijo del flyout.
- **Consolidar** con backlog Teams gaps «list_elements 7–8s max_depth=8» (TE-02+) — misma
  causa raíz walk ventana completa en Electron.
- **No duplica** `20260906_201430` (expand verify post-click) — distinto módulo/caller.
- **No duplica** notepad fast path MenuItem (aplicada) — patrón Win32 distinto.

## Test de abstracción (L4)

Cross-app: Slack/Discord/Electron con nav lateral + título que cambia por sección; WinUI apps
con NavigationView donde el panel central es el subtree accionable. Sin listas de
`automation_id` por producto — heurística bbox + título genérico.

## Esfuerzo observado

TE-10: 4637 ms inventario Button no requerido para met; TE-02: 7191 ms discovery baseline.
Agente TE-10 total ~14 s en tools de observación (list + find_text retorno).

## Criterio de aceptación

- [ ] `tests/test_list_elements_view_scope.py`: fixture árbol nav+content → `view_scope=true`
      devuelve solo hijos del pane ancho; `view_scope=false` sin regresión.
- [ ] Live Teams TE-10: `list_elements(role=Button, view_scope=true)` < **2000 ms** y
      count < 35 en vista Calendar.
- [ ] Respuesta incluye `view_scope_applied` y `duration_ms`.
- [ ] Documentado en `MCP_TOOLS_REFERENCE.md` § `list_elements`.
- [ ] Skill TE-10 (`204700`) referencia param como alternativa a omitir list_elements.

## Beneficios futuros

- TE-02 discovery y TE-10+ nav rail repetibles sin SLOW sistemático.
- Menos tokens al agente (lista corta acotada a vista activa).
- Complementa `within_automation_id` para popups vs vistas full-page Electron.

# list_elements: filtrar apps ajenas en ventana topmost / overlay compacto

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-07 23:46:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | `detection/element_scope.py`, `detection/backends/uia_backend.py`, `detection/orchestrator.py` |
| **Tool afectada** | `list_elements`, `spy_tree` |
| **Tipo de gap** | deteccion |
| **Nivel** | L4 |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** Con `set_target_window("Calculadora")`, tras activar **Always on Top** (ventana
compacta flotante `WS_EX_TOPMOST`), `list_elements` devuelve nodos de **Teams** y **Cursor**
mezclados con `ExitAlwaysOnTopButton`. El flujo F-24 quedó `met` funcionalmente, pero el
inventario está contaminado (`3486 ms`, outcome `partial`) y aumenta riesgo de click ajeno.

**Solución:** (1) Detectar ventana objetivo topmost/overlay (`GetWindowLong` +
ratio client_rect vs área de pantalla). (2) En ese modo, **obligar** walk UIA desde HWND
objetivo (`Desktop.window(handle=hwnd).descendants`) — no barrido desktop/spatial que incluya
capas z-order inferiores. (3) Endurecer `element_in_window_scope`: rechazar elementos cuyo
`process_id` no esté en `process_ids` del target **aunque** `framework_id=XAML` o
`allow_renderer_pid` (renderer PID solo aplica cuando el **target** es Electron/WebView2,
no cuando la app objetivo es UWP shell). (4) Exponer metadatos:
`scope_mode: topmost_hwnd`, `foreign_pids_removed`.

**Dónde:** `resolve_window_scope` + `filter_elements_to_scope`; opcional flag en
`UIABackend.list_elements`; tests `tests/test_list_elements_topmost_scope.py`.

## Contexto del turno

- Lab `calculadora-2026-09-07`, flujo **F-24** execute_flow.
- `invoke_element(NormalAlwaysOnTopButton)` **198 ms** OK; id pasa a `ExitAlwaysOnTopButton`.
- `list_elements` post-pin: `ExitAlwaysOnTopButton` + **leak Teams/Cursor** — SLOW **3486 ms**.
- Evidencia: `runs/calculadora-2026-09-07/mcp-usage.jsonl` L91,
  `evidence.jsonl` L12 (`contaminacion Teams/Cursor en modo pin`).
- Skills: `awdui-mcp-automejora`, `action-narration`.

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| Teams/Cursor en list post-pin | deteccion | L4 | Sí (este archivo) |
| list_elements 3486 ms SLOW | performance | L3 | Backlog cache/cluster — no duplicar |
| find NormalAlwaysOnTop 8705 ms | performance | L4 | Consolidar `230300` depth-ladder |
| Agente buscó id pre-pin tras invoke | ejecucion | L2 | Skill lab `flows.json` ya anota swap |

No es `sintoma_app`: cualquier ventana topmost compacta sobre otra app (Snipping Tool,
Picture-in-Picture, Calculadora pin) puede filtrar mal si el walk no es HWND-bound.

## Cambio propuesto (pseudodiff)

```python
# element_scope.py
def _target_is_topmost_overlay(scope: dict) -> bool:
    hwnd = scope.get("target_hwnd") or _get_hwnd_for_window(scope["window_title"])
    if not hwnd:
        return False
    ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    topmost = bool(ex & WS_EX_TOPMOST)
    client = scope.get("client") or {}
    area = int(client.get("w", 0)) * int(client.get("h", 0))
    screen = user32.GetSystemMetrics(0) * user32.GetSystemMetrics(1)
    compact = screen and area < screen * 0.15
    return topmost or compact

def element_in_window_scope(...):
    ...
    if pids and pid and pid not in pids:
        if scope.get("topmost_overlay"):
            return False  # strict PID — no renderer bypass
        ...

def filter_elements_to_scope(...):
    scope = resolve_window_scope(window_title)
    scope["topmost_overlay"] = _target_is_topmost_overlay(scope)
    ...
```

```python
# uia_backend.py — list_elements
if scope.get("topmost_overlay") and target_hwnd:
    elements = _walk_hwnd_descendants_only(target_hwnd, ...)
```

## Verificación de duplicados

| Archivo | Relación |
|---------|----------|
| `124501_list-elements-target-window-scope` | **Aplicada** — scope PID+bbox; no cubre topmost overlay leak |
| `031000_filter-scope-uwp-screen-coords` | **Aplicada** — coords UWP; ortogonal |
| `125200_calculator-bleed-name-lightdismiss` | **Aplicada** — bleed intra-modo Calculadora, no Teams |
| `204701_list-elements-view-scope-electron` | Teams target — aquí target es UWP, leak inverso |

## Test de abstracción

Cualquier app con ventana flotante topmost (UWP pin, PiP, utilidades overlay) se beneficia
sin listas de `automation_id` por producto.

## Criterio de aceptación / tests

- [ ] Live Calculadora F-24 post-pin: `list_elements(role=Button)` sin TreeItem/list_id_* Teams
- [ ] `scoped_out` / `foreign_pids_removed` > 0 cuando había leak
- [ ] Modo normal (sin pin): sin regresión — inventario previo intacto
- [ ] Target Teams Electron: `allow_renderer_pid` sigue activo cuando framework target es electron
- [ ] `pytest tests/test_list_elements_topmost_scope.py -q`

## Beneficios futuros

- Inventarios agenticos limpios en flujos overlay/pin sin coords manuales
- Reduce tokens y clicks erróneos en apps bajo la ventana flotante
- Complementa gate lab Calculadora § sin contaminación

## Esfuerzo observado

- F-24 execute: pin OK **198 ms**; list post-pin **3486 ms** con leak Teams — agente usó
  `spy_inspect(ExitAlwaysOnTopButton)` como workaround tras find lento.

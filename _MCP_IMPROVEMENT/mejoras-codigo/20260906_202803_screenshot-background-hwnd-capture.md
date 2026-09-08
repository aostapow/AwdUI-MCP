# screenshot: captura por HWND con target en background (sin robar foco)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-06 20:28:03 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | `tools/screenshot.py`, `tools/target_window.py` |
| **Tool afectada** | screenshot, take_screenshot_optimized |
| **Tipo de gap** | deteccion |
| **Nivel** | L4 |
| **MCP versión** | v0.4.0 |

## Resumen

**Problema:** Con `set_target_window(..., focus_policy="minimal")` y Teams en background
(Cursor enfocado), `screenshot(scope=window)` captura el **foreground** (Cursor) en lugar
del HWND objetivo. El agente debe forzar `focus_policy=always` en cada hito visual,
rompiendo el flujo agentico de observación en background documentado para TE harness.

**Solución:** (1) Cuando `scope=window|auto` y hay target HWND resuelto, capturar siempre
vía `PrintWindow` / `capture_window_image(hwnd)` **antes** de intentar screenshot de
monitor completo. (2) Solo llamar `ensure_focus_for_capture` / `do_focus_window` si
`focus_policy=always` **o** si `PrintWindow` devuelve imagen vacía/oculta (fallback).
(3) Metadata: `capture_method` (`hwnd_printwindow` | `foreground_monitor`),
`target_focused: bool`, `capture_hwnd`. (4) Alinear con `resolve_window_visual_rect` (fix
`120901` aplicada) para mismo HWND en UIA y captura.

**Dónde:** `capture_screenshot`, `_capture_window_by_title`, `resolve_capture_window` en
`screenshot.py`; tests `tests/test_screenshot_background_target.py`.

## Contexto del turno

TE-01+: screenshots con target Teams en background muestran Calendario/Cursor según foco
real, no el subárbol navegado. `teams/element-map.md` documenta workaround
`focus_policy=always` — síntoma de gap MCP, no solo routing.

`screenshot-scope-visual-rect` (`120901` aplicada) unificó rect UWP; no cubre captura
con ventana objetivo **no** en foreground.

## Cambio propuesto (pseudodiff)

```python
# screenshot.py
def capture_screenshot(..., window_title=None):
    hwnd = resolve_window_handle(window_title)
    if hwnd and scope in ("window", "auto"):
        img = capture_window_image(hwnd)  # PrintWindow first
        if img and not _is_blank(img):
            return {
                "image": encode(img),
                "capture_method": "hwnd_printwindow",
                "capture_hwnd": hwnd,
                "target_focused": is_window_in_foreground(hwnd),
            }
    # fallback: existing monitor capture + optional focus if policy=always
```

```python
# screenshot tool wrapper — focus only when policy demands
if wt and scope != "full" and get_focus_policy() == "always":
    do_focus_window(wt, "focus")
# remove unconditional ensure_focus_for_capture for minimal policy
```

## Test de abstracción (L4)

Cualquier flujo con `focus_policy=minimal` (Notepad, Teams, AST) que requiera evidencia
visual sin interrumpir al usuario — no solo Teams.

## Verificación de duplicados

- **Extiende** `120901` (rect/HWND resolución) — captura en background es capa adicional.
- Distinto de skill workaround `focus_policy=always` (mitigación agente, no fix MCP).

## Esfuerzo observado

Screenshots de hito TE-02/TE-03 potencialmente inválidos; agente debe re-enfocar Teams
para evidencia confiable.

## Criterio de aceptación

- [ ] Target en background + `focus_policy=minimal` → screenshot muestra ventana target.
- [ ] `focus_policy=always` sigue trayendo ventana al frente si PrintWindow falla.
- [ ] Respuesta incluye `capture_method` y `capture_hwnd`.
- [ ] Test pytest con mock HWND / ventana minimizada en background.

## Beneficios futuros

- Harness TE y metodología OBS→ACT→VERIFY con screenshots sin robar foco del agente.
- Coherente con misión MCP programático en background.

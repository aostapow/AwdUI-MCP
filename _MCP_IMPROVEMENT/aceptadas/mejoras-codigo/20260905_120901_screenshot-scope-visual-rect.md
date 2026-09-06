# screenshot scope=window alineado con resolve_window_visual_rect

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | aplicada |
| **Fecha** | 2026-09-05 12:09:01 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | tools/screenshot.py, tools/windows.py |
| **Tool afectada** | screenshot |
| **Tipo de gap** | deteccion |
| **Nivel** | L4 |
| **Impacto** | alto |

## Resumen

**Problema:** En Calculadora UWP, `screenshot(scope=full)` captura correctamente pero
`screenshot(scope=window)` falla o recorta mal. `_region_for_window` y
`_capture_window_by_title` usan `find_matching_window` que puede elegir
`CalculatorApp.exe` (CoreWindow) mientras `list_elements` y `resolve_window_visual_rect`
priorizan `ApplicationFrameHost.exe` (marco visible con title chrome y botones
fuera del CoreWindow).

**Solución:** Unificar resolución de rect de captura con `resolve_window_visual_rect`
(y `_best_window_candidate` para UWP). Exponer en respuesta `capture_hwnd`,
`capture_process` y `resolved_window_title` para debug.

**Dónde:** `_region_for_window`, `_capture_window_by_title` en `screenshot.py`.

## Contexto del turno

Inventario Standard: evidencia visual con `screenshot` full OK; `scope=window`
incorrecto — el agente no pudo usar captura acotada exigida por
`calculator-mcp-harness` (paso SCREENSHOT scope=window).

## Cambio propuesto (pseudodiff)

```python
# screenshot.py
def _region_for_window(window_title: str) -> Optional[dict]:
    from tools.windows import resolve_window_visual_rect, find_matching_window, do_list_windows
    visual = resolve_window_visual_rect(window_title)
    if visual:
        return visual
    # fallback actual con get_window_rect(hwnd) ...
```

```python
# _capture_window_by_title — usar mismo HWND que resolve_window_handle
from tools.windows import resolve_window_handle, resolve_window_visual_rect

hwnd = resolve_window_handle(window_title)
region = resolve_window_visual_rect(window_title) or _region_for_window_legacy(...)
```

**Respuesta enriquecida:**

```json
{
  "scope": "window",
  "resolved_window_title": "Calculadora",
  "capture_process": "ApplicationFrameHost.exe",
  "width": 425,
  "height": 675
}
```

## Verificación de duplicados

- `20260707_011000_mdi-window-scope.md` (aplicada): scope ventanas hijas MDI — distinto
  (WinForms MDI vs UWP frame host).
- `resolve_window_visual_rect` ya existe y tiene test en `test_window_visual_rect.py`
  pero **no** lo usa `screenshot.py` — gap de integración, no duplicado.

## Test de abstracción

Cualquier UWP/WinUI empaquetada en ApplicationFrameHost (Configuración, Fotos, etc.)
se beneficia del mismo criterio de ventana.

## Criterio de aceptación

- [ ] `tests/test_screenshot_tool.py`: mock con dos ventanas "Calculadora"
      (CalculatorApp + ApplicationFrameHost) → crop usa frame host.
- [ ] `scope=window` produce imagen con área ≥ CoreWindow y sin recorte del title bar.
- [ ] `scope=full` sin cambios.
- [ ] Documentar en `MCP_TOOLS_REFERENCE.md` que UWP usa frame host para crop.

## Beneficios futuros

- Evidencia del harness Calculadora con `scope=window` como exige la skill.
- Menor payload vs full screen sin perder chrome relevante (historial, memoria).
- Consistencia visual entre anotaciones UIA y screenshot.

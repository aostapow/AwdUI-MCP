# NP-01 — Discovery + mapa UIA completo

## Objetivo
Inventario programático de la ventana principal Notepad antes de cualquier acción destructiva.

## Precondiciones
- `launch_app("notepad.exe", reuse=true)`

## Fase 0 — Ventana
```
list_windows                          → "Sin título: Bloc de notas"
set_target_window("Bloc de notas")
get_target_window                       → focus_policy=minimal
```

## Fase 1 — Shell
```
detect_framework(window_title="Bloc de notas")     → win32, class Notepad (150ms)
detection_health(window_title="Bloc de notas")     → uia/msaa/win32 OK
observe_ui_tool(window_title="Bloc de notas")      → fingerprint + modales
ui_fingerprint(window_title="Bloc de notas")       → baseline hash
```

## Fase 2–3 — Árbol
```
list_elements(window_title="Bloc de notas", max_depth=3)   → 24 elementos (3794ms SLOW)
spy_tree(window_title="Bloc de notas", max_depth=4)      → jerarquía completa
ascii_ui_view(window_title="Bloc de notas")                → mapa ASCII + eN keys
list_elements(role="MenuItem", max_depth=4)                → 5 menús top
discover_control_interaction(name="Archivo", role="MenuItem")
discover_control_interaction(automation_id="15")           → editor Value
spy_inspect(automation_id="15")                            → Document, ValuePattern
get_element_properties(automation_id="15")
element_at_point(x=400, y=200)                             → pick editor
```

## Verificación
- Editor id=15 expuesto con ValuePattern
- 5 MenuItem top-level visibles
- StatusBar id=1025 con Text hijos (línea, zoom, UTF-8)

## Evidencia (2026-09-06)
| Tool | timing_ms | verdict |
|------|-----------|---------|
| list_elements depth=3 | 3794 | slow |
| detect_framework | ~150 | ok |
| spy_inspect editor | ~350 | ok |
| ascii_ui_view | ~1200 | ok |

## Screenshot
`screenshot(scope=window)` — ventana vacía con barra estado

# Recovery Teams (Electron)

| Nivel | Cuándo | Acción |
|-------|--------|--------|
| L0 | Siempre | `list_windows` + `get_focused_element` |
| L1 | Modal / picker abierto | `send_keys Escape` o botón Cancelar UIA → verify cierre |
| L2 | Foco perdido | `focus_window("Microsoft Teams")` o título parcial `Teams` |
| L3 | Stale UIA / not_found | `launch_app(ms-teams, replace=true)` + `set_target_window` |
| L4 | Post-relaunch | Re-ejecutar TE-01 baseline antes del flujo interrumpido |

Señales stale: `stale_instance`, `Window not found`, árbol 0 nodos tras launch OK.

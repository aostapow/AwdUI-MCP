# NP-29 — Guardar como solo teclado (Alt cascade)

**Estado:** met  
**Tools MCP:** `focus_window`, `send_keys`, `list_windows`, `get_focused_element`, `set_element_value`, `fill_form`, `invoke_element`, `click_element`, `screenshot`  
**Recovery típico:** L1

## Objetivo

Abrir **Guardar como** sin `invoke_element` en menú — solo **Alt cascade** o Ctrl+Mayús+S; verify modal + cancelar con list_windows.

## Pasos

### Paso 0 — Baseline
| | |
|---|---|
| **Act** | `list_windows` |
| **Verify A** | Sin Guardar como #32770 |
| **Verify B** | Notepad presente |

### Paso 1 — Seed + dirty
| | |
|---|---|
| **Act** | `set_element_value(id=15, value="NP29_SAVEAS_KEYBOARD_TEST")` |
| **Verify** | read_element OK |
| **Verify B** | Título ventana muestra `*` (sin guardar) si aplica |

### Paso 2 — Focus
| | |
|---|---|
| **Act** | `focus_window("Bloc de notas")` |
| **Verify** | get_focused_element → editor |

### Paso 3 — Atajo Guardar como
| | |
|---|---|
| **Act** | `send_keys("ctrl+shift+s")` |
| **Verify A** | `list_windows` → `Guardar como` |
| **Verify B** | get_focused_element → Edit Nombre archivo id=1001 |
| **Verify C** | Timing anotado |

### Paso 4 — Nombre archivo (sin guardar disco)
| | |
|---|---|
| **Act** | `set_target_window("Guardar como")` |
| **Act** | `set_element_value(automation_id="1001", value="np29_test_keyboard.txt")` |
| **Verify A** | Value OK |
| **Act** | `list_elements(role="Button", max_depth=4)` |
| **Verify B** | Botón Guardar id=1 presente |

### Paso 5 — Cancelar (no persistir)
| | |
|---|---|
| **Act** | `click_element(automation_id="2", window_title="Guardar como")` |
| **Verify A** | `list_windows` → **sin** Guardar como |
| **Verify B** | get_focused_element → Notepad editor |
| **Act** | `set_target_window("Bloc de notas")` |
| **Verify C** | read_element aún NP29_SAVEAS_KEYBOARD_TEST |

### Paso 6 — Variante Alt cascade (opcional)
| | |
|---|---|
| **Act** | `send_keys("alt")` luego secuencia menú si soportado — o documentar skip |
| **Verify** | Mismo modal Guardar como si ejecutado |
| **Cleanup** | Cancelar + list_windows |

### Paso 7 — Hito
| | |
|---|---|
| **Act** | `screenshot(scope="window")` Notepad |
| **Verify** | list_windows limpio |

## Checkpoints

| CP | Verify fuerte |
|----|---------------|
| CP-3 | list_windows Guardar como + focus Edit 1001 |
| CP-5 | Cancelar → ausencia modal + contenido preservado |

## Referencias

- [NP-04-save-as.md](NP-04-save-as.md)
- [modals/save-as.md](../modals/save-as.md)

# NP-27 — Insertar fecha y hora

**Estado:** met  
**Tools MCP:** `focus_window`, `invoke_element`, `list_elements`, `read_element`, `set_element_value`, `send_keys`, `list_windows`, `screenshot`  
**Recovery típico:** L2

## Objetivo

Insertar timestamp vía menú **Edición → Fecha y hora** (Win11 ES) y verify en editor + status bar.

## Pasos

### Paso 0 — Baseline
| | |
|---|---|
| **Act** | `list_windows` |
| **Verify** | Sin modales; Notepad presente |

### Paso 1 — Editor limpio
| | |
|---|---|
| **Act** | `set_element_value(id=15, value="")` |
| **Verify A** | read_element vacío |
| **Verify B** | Status Línea 1, columna 1 |

### Paso 2 — Focus
| | |
|---|---|
| **Act** | `focus_window("Bloc de notas")` |
| **Verify** | get_focused_element → editor |

### Paso 3 — Menú Edición
| | |
|---|---|
| **Act** | `invoke_element(name="Edición")` |
| **Act** | `list_elements(role="MenuItem", max_depth=3)` |
| **Verify A** | Existe item `Fecha y hora` o equivalente ES (anotar name exacto) |
| **Act** | `invoke_element(name="Fecha y hora")` |
| **Verify B** | **No** abre modal #32770 (acción directa) |

### Paso 4 — Verify inserción
| | |
|---|---|
| **Act** | `read_element(id=15)` |
| **Verify A** | value length > 0 |
| **Verify B** | Patrón fecha reconocible (dd/mm/aaaa o similar — anotar literal) |
| **Verify C** | Status col > 1 |

### Paso 5 — Segunda inserción
| | |
|---|---|
| **Act** | `send_keys("enter")` |
| **Act** | Repetir invoke Fecha y hora |
| **Verify A** | read_element 2 líneas con timestamps |
| **Verify B** | Status → Línea 2 |

### Paso 6 — Undo
| | |
|---|---|
| **Act** | `send_keys("ctrl+z")` |
| **Verify A** | read_element vuelve a 1 línea |
| **Act** | `send_keys("ctrl+z")` |
| **Verify B** | read_element vacío |

### Paso 7 — Hito
| | |
|---|---|
| **Act** | `screenshot(scope="window")` |
| **Verify** | list_windows limpio |

## Checkpoints

| CP | Verify fuerte |
|----|---------------|
| CP-3 | list_elements confirma item menú antes de invoke |
| CP-4 | read_element timestamp no vacío |
| CP-6 | undo chain revierte 2 inserciones |

## Notas Win11 ES

- Nombre menú puede variar; usar `list_elements` antes de invoke — no hardcodear sin verify.
- Si item deshabilitado → documentar build; marcar partial.

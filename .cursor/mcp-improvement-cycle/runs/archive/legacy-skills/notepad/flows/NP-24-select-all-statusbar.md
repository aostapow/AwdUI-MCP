# NP-24 — Seleccionar todo + status bar

**Estado:** met  
**Tools MCP:** `focus_window`, `send_keys`, `read_element`, `set_element_value`, `list_elements`, `clipboard`, `screenshot`, `list_windows`  
**Recovery típico:** L2

## Objetivo

Validar selección total, efecto en status bar (línea/col al seleccionar bloque) y clipboard coherente.

**Win11 ES:** `Ctrl+A` = **Abrir** (Archivo id=2) — abre modal guardar/Abrir. **Seleccionar todo = `Ctrl+E`** (Edición id=25).

## Pasos

### Paso 0 — Baseline
| | |
|---|---|
| **Act** | `list_windows` |
| **Verify** | Sin modales; Notepad presente |

### Paso 1 — Seed multilínea
| | |
|---|---|
| **Act** | `set_element_value(id=15, value="line A\nline B\nline C\nline D\nline E")` |
| **Verify A** | read_element 5 líneas |
| **Verify B** | Status → `Línea 1, columna 1` |

### Paso 2 — Focus editor
| | |
|---|---|
| **Act** | `focus_window("Bloc de notas")` |
| **Act** | `click_element(automation_id="15")` o coords centro editor |
| **Verify** | `get_focused_element` → Document/Edit |

### Paso 3 — Seleccionar todo (Ctrl+E Win11 ES)
| | |
|---|---|
| **Act** | `send_keys("ctrl+e")` — **no** `ctrl+a` (Abrir en Win11 ES) |
| **Verify A** | Status bar cambia (anotar línea/col — suele mostrar selección o L1 col 1) |
| **Verify B** | `screenshot` — texto resaltado visible (hito) |

### Paso 4 — Copiar selección
| | |
|---|---|
| **Act** | `send_keys("ctrl+c")` |
| **Act** | `clipboard(action="read")` |
| **Verify A** | Clipboard contiene las 5 líneas completas |
| **Verify B** | Longitud clipboard ≥ longitud read_element value |

### Paso 5 — Deseleccionar
| | |
|---|---|
| **Act** | `send_keys("right")` |
| **Verify** | Status col incrementa |

### Paso 6 — Seleccionar todo + Delete
| | |
|---|---|
| **Act** | `send_keys("ctrl+e")` |
| **Act** | `send_keys("delete")` |
| **Verify A** | `read_element` id=15 value vacío o solo whitespace |
| **Verify B** | Status → Línea 1, columna 1 |

### Paso 7 — Restore via clipboard
| | |
|---|---|
| **Act** | `send_keys("ctrl+v")` |
| **Verify A** | read_element restaura 5 líneas |
| **Verify B** | Status coherente |

### Paso 8 — Hito
| | |
|---|---|
| **Act** | `screenshot(scope="window")` |
| **Verify** | `list_windows` limpio |

## Checkpoints

| CP | Verify fuerte |
|----|---------------|
| CP-3 | screenshot selección visible |
| CP-4 | clipboard == editor content |
| CP-6 | editor vacío post-delete |

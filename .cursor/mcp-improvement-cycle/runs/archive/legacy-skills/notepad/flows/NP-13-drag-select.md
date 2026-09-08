# NP-13 — Selección drag texto

**Estado:** met (2026-09-06)  
**Tools MCP:** `set_element_value`, `get_element_bounds`, `focus_window`, `send_keys`, `drag`, `clipboard`, `screenshot`

## Pasos

### Paso 0 — Baseline
| | |
|---|---|
| **Act** | `list_windows` |
| **Verify** | Sin modales |

### Paso 1 — Seed
| | |
|---|---|
| **Act** | `set_element_value(id=15, value="drag test alpha beta gamma")` |
| **Verify** | `read_element` value OK |

### Paso 2 — Bounds
| | |
|---|---|
| **Act** | `get_element_bounds(automation_id="15")` |
| **Verify** | bbox x,y,width,height (ej. x=302 y=62 w=860 h=422) |

### Paso 3 — Drag select
| | |
|---|---|
| **Act** | `focus_window` → `send_keys("ctrl+home")` |
| **Act** | `drag(from_x=200, from_y=80, to_x=450, to_y=80)` |
| **Nota** | Ajustar coords según bbox; primer intento (310,85)→(520,85) seleccionó solo "gamma" |

### Paso 4 — Copiar y verificar
| | |
|---|---|
| **Act** | `send_keys("ctrl+c")` |
| **Verify** | `clipboard(action="read")` → `alpha beta gamma` |

### Paso 5 — Hito
| | |
|---|---|
| **Act** | `screenshot` — selección azul visible |

## Evidencia 2026-09-06

- drag 200,80→450,80 OK
- clipboard: `alpha beta gamma`
- screenshot: selección visible Línea 1 col 27

## Referencias

- [protocol/agentic-execution.md](../protocol/agentic-execution.md)

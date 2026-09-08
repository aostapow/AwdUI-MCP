# NP-25 — Cortar / Copiar / Pegar (menú contextual)

**Estado:** met  
**Tools MCP:** `set_element_value`, `read_element`, `right_click_element`, `list_elements`, `invoke_element`, `click_element`, `clipboard`, `list_windows`, `screenshot`  
**Recovery típico:** L2

## Objetivo

Cadena completa vía **menú contextual** (no solo atajos): selección → Cortar → Pegar → verify value.

## Pasos

### Paso 0 — Baseline
| | |
|---|---|
| **Act** | `list_windows` |
| **Verify** | 0 modales #32770 |

### Paso 1 — Seed
| | |
|---|---|
| **Act** | `set_element_value(id=15, value="ALPHA BETA GAMMA")` |
| **Verify** | read_element OK |

### Paso 2 — Seleccionar palabra (drag o doble clic)
| | |
|---|---|
| **Act** | `get_element_bounds(automation_id="15")` |
| **Act** | `drag` sobre substring BETA (coords documentadas en evidencia) |
| **Verify A** | screenshot selección parcial |
| **Verify B** | Status col cambia |

### Paso 3 — Menú contextual
| | |
|---|---|
| **Act** | `right_click_element(automation_id="15")` |
| **Verify A** | `list_elements(role="MenuItem", max_depth=3)` → Cortar, Copiar, Pegar |
| **Verify B** | Ningún modal #32770 |

### Paso 4 — Copiar
| | |
|---|---|
| **Act** | `invoke_element(name="Copiar")` o click MenuItem Copiar |
| **Act** | `clipboard(read)` |
| **Verify** | Clipboard contiene `BETA` o selección |

### Paso 5 — Cortar
| | |
|---|---|
| **Act** | Reseleccionar BETA si necesario |
| **Act** | `invoke_element(name="Cortar")` |
| **Verify A** | read_element ya no contiene `BETA` (o espacio colapsado) |
| **Verify B** | clipboard aún tiene BETA |

### Paso 6 — Pegar al final
| | |
|---|---|
| **Act** | `send_keys("ctrl+end")` |
| **Act** | `invoke_element(name="Pegar")` |
| **Verify A** | read_element contiene BETA al final |
| **Verify B** | Orden palabras documentado en evidencia |

### Paso 7 — Cerrar menú contextual
| | |
|---|---|
| **Act** | `send_keys("escape")` |
| **Verify** | list_elements sin MenuItem flotante stale |

### Paso 8 — Hito
| | |
|---|---|
| **Act** | `screenshot(scope="window")` |
| **Verify** | list_windows limpio |

## Checkpoints

| CP | Gate |
|----|------|
| CP-3 | Menú contextual 3+ items UIA |
| CP-5 | Cortar reduce editor + clipboard OK |
| CP-6 | Pegar restaura substring |

## Referencias

- [NP-14-context-menu.md](NP-14-context-menu.md)
- [NP-13-drag-select.md](NP-13-drag-select.md)

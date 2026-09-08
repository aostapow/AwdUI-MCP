# NP-22 — Buscar siguiente + F3 (cadena de ocurrencias)

**Estado:** met (2026-09-06)  
**Tools MCP:** `list_windows`, `focus_window`, `read_element`, `set_element_value`, `invoke_element`, `click_element`, `send_keys`, `list_elements`, `screenshot`  
**Recovery típico:** L1 cierre modal Buscar

## Objetivo

Verificar búsqueda iterativa: modal Buscar → varias ocurrencias → **F3** (Buscar siguiente) con status bar como verify fuerte.

## Precondiciones

- [ ] NP-21 met o baseline equivalente
- [ ] Win11 ES: **Ctrl+B** o menú Edición → Buscar id=21 (no Ctrl+F Bing)

## Pasos

### Paso 0 — Baseline
| | |
|---|---|
| **Act** | `list_windows` |
| **Verify A** | Sin `Buscar` #32770 |
| **Verify B** | Notepad `Bloc de notas` presente |

### Paso 1 — Seed multi-ocurrencia
| | |
|---|---|
| **Act** | `focus_window("Bloc de notas")` |
| **Act** | `set_element_value(id=15, value="needle line1\nneedle line2\nneedle line3\nno match here\nneedle line5")` |
| **Verify A** | `read_element` id=15 → 5 líneas |
| **Verify B** | `read_element` contiene exactamente 4× substring `needle` |

### Paso 2 — Cursor inicio
| | |
|---|---|
| **Act** | `send_keys("ctrl+home")` |
| **Verify** | Status bar → `Línea 1` (list_elements Text o read status) |

### Paso 3 — Abrir Buscar
| | |
|---|---|
| **Act** | `invoke_element(name="Edición")` |
| **Act** | `invoke_element(automation_id="21")` |
| **Verify A** | `list_windows` → `Buscar` |
| **Verify B** | `get_focused_element` → Edit id=1152 nombre `Buscar:` |

### Paso 4 — Término
| | |
|---|---|
| **Act** | `set_element_value(automation_id="1152", value="needle", window_title="Buscar")` |
| **Verify** | OK ValuePattern |

### Paso 5 — Primera ocurrencia (botón)
| | |
|---|---|
| **Act** | `click_element(automation_id="1", window_title="Buscar")` |
| **Verify A** | click verified |
| **Verify B** | Status Notepad → `Línea 1` (primera needle) — anotar col |
| **Verify C** | Modal Buscar **sigue abierto** en `list_windows` |

### Paso 6 — Segunda ocurrencia (F3)
| | |
|---|---|
| **Act** | `send_keys("f3")` |
| **Verify A** | Status → `Línea 2` |
| **Act** | `send_keys("f3")` |
| **Verify B** | Status → `Línea 3` |
| **Act** | `send_keys("f3")` |
| **Verify C** | Status → `Línea 5` (salta línea 4 sin needle) |

### Paso 7 — Wrap / fin cadena
| | |
|---|---|
| **Act** | `send_keys("f3")` |
| **Verify** | Comportamiento documentado: vuelve a L1 o mensaje — anotar (no asumir) |
| **Act** | `screenshot(scope="window")` hito selección visible |

### Paso 8 — Cierre modal (verify estructural)
| | |
|---|---|
| **Act** | `click_element(automation_id="2", window_title="Buscar")` |
| **Verify A** | `list_windows` → **sin** título `Buscar` |
| **Verify B** | `get_focused_element` → editor id=15 |
| **Act** | `set_target_window("Bloc de notas")` |

## Checkpoints obligatorios

| # | Después de | Verify mínima | Verify fuerte |
|---|------------|---------------|---------------|
| 1 | Seed | read_element 4 needles | conteo manual en value |
| 2 | click Buscar siguiente | status L1 | modal aún abierto |
| 3 | cada F3 | status línea avanza | screenshot cada 2 saltos |
| 4 | Cancelar | list_windows limpio | focus editor |

## Referencias

- [NP-10-find.md](NP-10-find.md)
- [modals/find-replace.md](../modals/find-replace.md)

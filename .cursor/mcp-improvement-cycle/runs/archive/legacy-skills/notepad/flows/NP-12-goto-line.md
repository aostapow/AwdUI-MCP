# NP-12 — Ir a línea

**Estado:** met (2026-09-06)  
**Tools MCP:** `invoke_element`, `spy_tree`, `set_element_value`, `click_element`, `list_elements`, `list_windows`, `screenshot`  
**Atajo Win11 ES:** Edición → Ir a... id=24 (**Ctrl+T**, no Ctrl+G)

## Precondiciones

- [ ] Baseline L0 sin modales
- [ ] Documento multi-línea (≥5 líneas)
- [ ] `ctrl+home` antes de goto (cursor línea 1)

## Gap resuelto

`list_elements(max_depth=3)` en modal **no expone** el Edit numérico.  
**Solución:** `spy_tree(mode="raw", max_depth=8, window_title="Ir a la línea")` → `Edit "Número de línea:" id=258`.

## Pasos

### Paso 0 — Baseline
| | |
|---|---|
| **Act** | `list_windows` |
| **Verify** | 0 modales `#32770` |

### Paso 1 — Seed
| | |
|---|---|
| **Act** | `set_element_value` id=15 líneas line1..line10 |
| **Verify** | `read_element` contiene line10 |

### Paso 2 — Cursor inicio
| | |
|---|---|
| **Act** | `send_keys("ctrl+home")` |

### Paso 3 — Abrir diálogo
| | |
|---|---|
| **Act** | `invoke_element(Edición)` → `invoke_element(automation_id="24")` |
| **Verify** | `list_windows` → `Ir a la línea` #32770 |

### Paso 4 — Mapear input (spy)
| | |
|---|---|
| **Act** | `spy_tree(mode="raw", max_depth=8, window_title="Ir a la línea")` |
| **Verify** | Edit id=**258** name `Número de línea:` |

### Paso 5 — Ir a línea 5
| | |
|---|---|
| **Act** | `set_element_value(automation_id="258", value="5", window_title="Ir a la línea")` |
| **Act** | `click_element(automation_id="1", window_title="Ir a la línea")` |
| **Verify A** | `list_windows` sin modal |
| **Verify B** | Status bar Text `Línea 5, columna 1` |

### Paso 6 — Hito
| | |
|---|---|
| **Act** | `screenshot(scope="window")` |

## Evidencia 2026-09-06

- spy_tree: id=258 Edit Número de línea
- Status: Línea 5, columna 1
- Screenshot: line5 visible en editor

## Referencias

- [protocol/agentic-execution.md](../protocol/agentic-execution.md)

# NP-11 — Reemplazar (Win11 ES — detallado)

**Estado:** met (2026-09-06) · revalidar con NP-23  
**Tools MCP:** `list_windows`, `focus_window`, `read_element`, `set_element_value`, `invoke_element`, `click_element`, `send_keys`, `screenshot`  
**Recovery típico:** L1 cierre modal Reemplazar

## Win11 ES

| Atajo clásico | Win11 ES Notepad |
|---------------|------------------|
| Ctrl+H | **Ctrl+R** → Reemplazar (MenuItem id=23) |

## Precondiciones

- [ ] Baseline L0: 0 modales `#32770`
- [ ] Seed documentado (paso 2)

## Pasos

### Paso 0 — Baseline
| | |
|---|---|
| **Act** | `list_windows` |
| **Verify A** | Sin Reemplazar/Buscar |
| **Verify B** | Notepad presente |

### Paso 1 — Focus
| | |
|---|---|
| **Act** | `focus_window("Bloc de notas")` |
| **Verify** | get_focused_element → id=15 |

### Paso 2 — Seed
| | |
|---|---|
| **Act** | `set_element_value(id=15, value="one alpha two\nthree alpha four")` |
| **Verify A** | read_element OK |
| **Verify B** | 2× `alpha` en value |

### Paso 3 — Abrir Reemplazar
| | |
|---|---|
| **Act** | `invoke_element(name="Edición")` |
| **Act** | `invoke_element(automation_id="23")` |
| **Verify A** | list_windows → `Reemplazar` |
| **Verify B** | Edit 1152 + 1153 en modal |

### Paso 4 — Campos
| | |
|---|---|
| **Act** | `set_element_value(1152, "alpha", window_title="Reemplazar")` |
| **Act** | `set_element_value(1153, "beta", window_title="Reemplazar")` |
| **Verify** | ambos OK |

### Paso 5 — Reemplazar todo
| | |
|---|---|
| **Act** | `click_element(automation_id="1025", window_title="Reemplazar")` |
| **Verify A** | click verified |
| **Verify B** | read_element → `one beta two` / `three beta four` |

### Paso 6 — Cierre modal
| | |
|---|---|
| **Act** | Si modal abierto: Cancelar id=2 |
| **Verify A** | list_windows sin Reemplazar |
| **Verify B** | set_target_window Notepad |

### Paso 7 — Hito
| | |
|---|---|
| **Act** | `screenshot(scope="window")` |

## Evidencia 2026-09-06

- Reemplazar todo id=1025; read_element beta one/two/three

## Referencias

- [NP-23-replace-all-verify.md](NP-23-replace-all-verify.md) (cadena extendida)
- [modals/find-replace.md](../modals/find-replace.md)

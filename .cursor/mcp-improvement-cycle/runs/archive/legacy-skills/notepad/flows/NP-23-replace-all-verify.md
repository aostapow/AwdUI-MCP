# NP-23 — Reemplazar todo + verify editor

**Estado:** pending  
**Tools MCP:** `list_windows`, `focus_window`, `read_element`, `set_element_value`, `invoke_element`, `click_element`, `send_keys`, `screenshot`  
**Recovery típico:** L1

## Objetivo

Flujo completo Reemplazar (Win11 ES **Ctrl+R**, id=23) con **Reemplazar todo** y verify por `read_element` + conteo ocurrencias.

## Pasos

### Paso 0 — Baseline
| | |
|---|---|
| **Act** | `list_windows` |
| **Verify** | 0 modales `#32770`; Notepad presente |

### Paso 1 — Seed
| | |
|---|---|
| **Act** | `set_element_value(id=15, value="foo bar\nfoo baz\nbar foo\nfoo end")` |
| **Verify A** | `read_element` OK |
| **Verify B** | Contar `foo` = 4 ocurrencias en value |

### Paso 2 — Abrir Reemplazar
| | |
|---|---|
| **Act** | `invoke_element(name="Edición")` |
| **Act** | `invoke_element(automation_id="23")` |
| **Verify A** | `list_windows` → `Reemplazar` |
| **Verify B** | `list_elements` modal → Edit id=1152 + id=1153 |

### Paso 3 — Campos buscar/reemplazar
| | |
|---|---|
| **Act** | `set_element_value(automation_id="1152", value="foo", window_title="Reemplazar")` |
| **Verify A** | OK |
| **Act** | `set_element_value(automation_id="1153", value="BAR", window_title="Reemplazar")` |
| **Verify B** | OK ambos campos |

### Paso 4 — Reemplazar todo
| | |
|---|---|
| **Act** | `click_element(automation_id="1025", window_title="Reemplazar")` |
| **Verify A** | click verified (Reemplazar todo) |
| **Verify B** | Modal puede cerrarse o quedar — anotar |
| **Act** | `list_windows` |
| **Verify C** | Sin `Reemplazar` (si persiste → click Cancelar id=2 + verify) |

### Paso 5 — Verify contenido
| | |
|---|---|
| **Act** | `read_element(automation_id="15")` |
| **Verify A** | 0 ocurrencias de `foo` |
| **Verify B** | 3 ocurrencias de `BAR` (bar→BAR solo si case — documentar) |
| **Verify C** | Líneas esperadas: `BAR bar`, `BAR baz`, `bar BAR`, `BAR end` |

### Paso 6 — Status bar
| | |
|---|---|
| **Act** | `list_elements(role="Text", max_depth=6)` |
| **Verify** | Línea/col coherentes post-reemplazo |

### Paso 7 — Hito + cleanup
| | |
|---|---|
| **Act** | `screenshot(scope="window")` |
| **Verify** | `list_windows` limpio |
| **Act** | `set_target_window("Bloc de notas")` |

## Checkpoints

| CP | Gate |
|----|------|
| CP-1 | Seed 4× foo documentado |
| CP-2 | Modal Reemplazar campos 1152/1153 |
| CP-3 | Post reemplazar: 0 foo en read_element |
| CP-4 | Cierre modal list_windows |

## Referencias

- [NP-11-replace.md](NP-11-replace.md) (evidencia histórica met)
- [modals/find-replace.md](../modals/find-replace.md)

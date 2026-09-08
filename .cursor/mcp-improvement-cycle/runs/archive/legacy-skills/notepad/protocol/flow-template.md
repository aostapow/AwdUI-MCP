# NP-XX — <Título del flujo>

**Estado:** pending | partial | met  
**Última verificación:** YYYY-MM-DD  
**Tools MCP:** (lista)  
**Recovery típico:** L1 | L2 | L3

## Precondiciones

- [ ] Baseline limpio ([recovery.md](recovery.md))
- [ ] `set_target_window("Bloc de notas")`
- [ ] (opcional) estado previo del documento: ...

## Pasos

### Paso 0 — Baseline
| | |
|---|---|
| **Act** | `list_windows` |
| **Esperado** | Sin modales `#32770` de notepad |
| **Verify** | Anotar títulos; si modal → L1 antes de seguir |

### Paso 1 — <nombre>
| | |
|---|---|
| **Act** | `` `tool`(params) `` |
| **Esperado** | ... |
| **Verify** | `` `tool_verify`(params) `` → ... |
| **Si falla** | Hipótesis → L? → reintentar paso 1 |

### Paso N — Cierre
| | |
|---|---|
| **Act** | `screenshot` scope=window (hito) |
| **Verify** | Estado final documentado |
| **Cleanup** | Cerrar modales; `set_target_window("Bloc de notas")` |

## Tabla de checkpoints (obligatoria NP-21+)

| CP | Gate | Verify mínima | Verify fuerte |
|----|------|---------------|---------------|
| CP-0 | Baseline | list_windows sin #32770 | check_session_status |
| CP-N | Post-modal | título ausente list_windows | get_focused_element padre |
| CP-final | Hito | screenshot citado | read_element estado esperado |

## Evidencia registrada

| Campo | Valor |
|-------|-------|
| timing_ms | |
| notepad_matrix | met/partial/fail |
| notas | |

## Referencias

- [element-map.md](../element-map.md)
- [modals/](../modals/) si aplica

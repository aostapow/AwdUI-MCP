# NP-18 — Watcher + modal async

**Estado:** met (2026-09-06)  
**Tools MCP:** `start_watcher`, `focus_window`, `send_keys`, `get_notifications`, `stop_watcher`, `list_windows`, `invoke_element`, `screenshot`  
**Recovery típico:** L1 cierre `Guardar como` si queda abierto tras test

## Precondiciones

- [ ] Baseline limpio — sin modales `#32770` ([recovery.md](../protocol/recovery.md))
- [ ] Notepad con documento **modificado** (título `*archivo: Bloc de notas`)
- [ ] `set_target_window("Bloc de notas")`

## Pasos

### Paso 0 — Baseline ventanas
| | |
|---|---|
| **Act** | `list_windows` |
| **Esperado** | Solo ventana principal Notepad; sin `Guardar como` / `Abrir` |
| **Verify** | Contar `#32770/notepad.exe` = 0 |
| **Si falla** | Recovery L1 → reintentar paso 0 |

### Paso 1 — Iniciar watcher
| | |
|---|---|
| **Act** | `start_watcher(poll_interval=2)` |
| **Esperado** | "Watcher started" |
| **Verify** | Output confirma monitoreo activo |
| **Si falla** | No continuar; watcher es prerequisito |

### Paso 2 — Enfocar Notepad
| | |
|---|---|
| **Act** | `focus_window(title="Bloc de notas")` |
| **Esperado** | "Focused window: *... Bloc de notas" |
| **Verify** | `get_focused_element` → control de Notepad (no picker) |
| **Si falla** | Recovery L2 |

### Paso 3 — Abrir Guardar como (async)
| | |
|---|---|
| **Act** | `send_keys(keys="ctrl+shift+s")` |
| **Esperado** | Modal `Guardar como` aparece |
| **Verify** | `list_windows` → fila `Guardar como [#32770/notepad.exe]` |
| **Si falla** | Menú Archivo → Guardar como id=4 vía `invoke_element` |

### Paso 4 — Leer notificación watcher
| | |
|---|---|
| **Act** | `get_notifications(clear=true)` |
| **Esperado** | ≥1 notificación WINDOW `"Guardar como"` con bbox |
| **Verify** | Texto incluye título y coordenadas; timing ~2s poll |
| **Si falla** | Repetir paso 3; verificar watcher activo (paso 1) |

### Paso 5 — Detener watcher
| | |
|---|---|
| **Act** | `stop_watcher` |
| **Esperado** | "Watcher stopped" |
| **Verify** | Output OK |

### Paso 6 — Cerrar modal (cleanup)
| | |
|---|---|
| **Act** | `focus_window("Guardar como")` → `invoke_element(name="Cancelar", window_title="Guardar como")` |
| **Esperado** | Modal cerrado |
| **Verify** | `list_windows` → **sin** `Guardar como` |
| **Si falla** | Recovery L1 (no confiar solo en Escape) |

### Paso 7 — Hito screenshot
| | |
|---|---|
| **Act** | `screenshot(scope="window", window_title="Bloc de notas")` |
| **Verify** | Solo editor visible; sin modal encima |

## Evidencia registrada (2026-09-06)

| Campo | Valor |
|-------|-------|
| notification | `17:27:00 WINDOW: "Guardar como" (93,63 960x241)` |
| list_windows | Guardar como #32770 presente tras ctrl+shift+s |
| notepad_matrix | **met** |

## Notas

- `start_event_monitor` **excluido** — blocker COM timeout; no mezclar con NP-18.
- Tras NP-18 **siempre** ejecutar paso 6 antes de otro flujo.

## Referencias

- [modals/save-as.md](../modals/save-as.md)
- [protocol/agentic-execution.md](../protocol/agentic-execution.md)

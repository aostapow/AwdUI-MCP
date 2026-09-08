# NP-30 — Stress modales secuenciales + recovery

**Estado:** met  
**Tools MCP:** `list_windows`, `focus_window`, `invoke_element`, `click_element`, `send_keys`, `set_element_value`, `read_element`, `set_target_window`, `screenshot`, `close_app`, `launch_app`  
**Recovery típico:** L1 entre modales; L3 al final si estado corrupto

## Objetivo

Abrir y cerrar **3 modales distintos en secuencia** sin mezclar flujos; **list_windows después de cada cierre** como gate obligatorio.

## Secuencia de modales

1. **Fuente** (Formato → Fuente)
2. **Buscar** (Edición → Buscar id=21)
3. **Configurar página** (Archivo id=5)

## Pasos

### Paso 0 — Baseline estricto
| | |
|---|---|
| **Act** | `list_windows` |
| **Verify A** | Anotar lista completa títulos |
| **Verify B** | 0 `#32770` notepad modales |
| **Verify C** | `check_session_status` target_alive |

### Paso 1 — Seed mínimo
| | |
|---|---|
| **Act** | `set_element_value(id=15, value="NP30_MODAL_STRESS")` |
| **Verify** | read_element OK |

---

### Modal 1 — Fuente

### Paso 2 — Abrir Fuente
| | |
|---|---|
| **Act** | `invoke_element(name="Formato")` |
| **Act** | invoke Fuente |
| **Verify A** | list_windows → `Fuente` |
| **Verify B** | List id=1000 visible |

### Paso 3 — Cancelar Fuente
| | |
|---|---|
| **Act** | `click_element(automation_id="2", window_title="Fuente")` |
| **Verify A** | list_windows **sin** Fuente |
| **Verify B** | set_target_window Notepad; read_element intacto |
| **Gate** | **STOP** si modal persiste → L1 |

---

### Modal 2 — Buscar

### Paso 4 — Abrir Buscar
| | |
|---|---|
| **Act** | `invoke_element(name="Edición")` |
| **Act** | `invoke_element(automation_id="21")` |
| **Verify A** | list_windows → Buscar |
| **Verify B** | Edit 1152 focused |

### Paso 5 — Cancelar Buscar
| | |
|---|---|
| **Act** | `click_element(automation_id="2", window_title="Buscar")` |
| **Verify A** | list_windows sin Buscar |
| **Verify B** | Sin Fuente ni Buscar simultáneos |
| **Gate** | STOP si 2+ modales #32770 |

---

### Modal 3 — Configurar página

### Paso 6 — Abrir Configurar página
| | |
|---|---|
| **Act** | `invoke_element(name="Archivo")` |
| **Act** | `invoke_element(automation_id="5")` |
| **Verify A** | list_windows → Configurar página |
| **Verify B** | get_focused_element dentro modal |

### Paso 7 — Cancelar Configurar página
| | |
|---|---|
| **Act** | click Cancelar en modal |
| **Verify A** | list_windows sin Configurar página |
| **Verify B** | 0 modales #32770 notepad |
| **Gate** | STOP → L1 o L3 |

---

### Paso 8 — Teclado post-modales
| | |
|---|---|
| **Act** | `focus_window("Bloc de notas")` |
| **Act** | `send_keys("ctrl+b")` — no debe abrir Bing si foco correcto |
| **Verify A** | Si abre Buscar → OK; si Bing → L2 focus fail |
| **Act** | Cancelar Buscar + list_windows |

### Paso 9 — Hito final
| | |
|---|---|
| **Act** | `screenshot(scope="window")` |
| **Verify A** | read_element NP30_MODAL_STRESS |
| **Verify B** | list_windows == baseline + Notepad (± ruido IDE) |

### Paso 10 — Cleanup opcional L3
| | |
|---|---|
| **Act** | Solo si algún gate falló: close_app notepad + launch_app + NP-21 |
| **Verify** | Baseline limpio |

## Matriz gates (obligatoria)

| Tras modal | list_windows | Acción si fail |
|------------|--------------|----------------|
| Fuente cancel | sin Fuente | L1 focus + Cancelar |
| Buscar cancel | sin Buscar | L1 |
| Página cancel | sin Configurar | L1 |
| Post ctrl+b | sin Bing panel | L2 focus_window |

## Referencias

- [protocol/recovery.md](../protocol/recovery.md)
- [NP-08-font.md](NP-08-font.md), [NP-10-find.md](NP-10-find.md), [NP-20-print-page.md](NP-20-print-page.md)

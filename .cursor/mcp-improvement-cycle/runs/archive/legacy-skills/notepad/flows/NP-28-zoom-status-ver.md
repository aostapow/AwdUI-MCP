# NP-28 — Zoom barra de estado (menú Ver)

**Estado:** met  
**Tools MCP:** `invoke_element`, `list_elements`, `element_exists`, `list_windows`, `read_element`, `screenshot`, `send_keys`  
**Recovery típico:** L2

## Objetivo

Toggle **Barra de estado** y **Zoom** vía menú Ver; verify hijos Text id=1025 y porcentaje en status.

## Pasos

### Paso 0 — Baseline
| | |
|---|---|
| **Act** | `list_windows` |
| **Verify** | Notepad presente; 0 modales |

### Paso 1 — Status bar visible
| | |
|---|---|
| **Act** | `element_exists(automation_id="1025")` |
| **Verify A** | OK |
| **Act** | `list_elements(role="Text", max_depth=6)` |
| **Verify B** | Text `100%` presente |
| **Verify C** | Text `UTF-8` presente |

### Paso 2 — Ocultar barra (Ver)
| | |
|---|---|
| **Act** | `invoke_element(name="Ver")` |
| **Act** | `invoke_element(name="Barra de estado")` o automation_id documentado NP-09 |
| **Verify A** | `element_exists(1025)` → NOT FOUND |
| **Verify B** | screenshot — barra inferior ausente |
| **Act** | `list_windows` |
| **Verify C** | Sin modales |

### Paso 3 — Restaurar barra
| | |
|---|---|
| **Act** | `invoke_element(name="Ver")` |
| **Act** | `invoke_element(name="Barra de estado")` |
| **Verify A** | element_exists 1025 OK |
| **Verify B** | Text 100% visible de nuevo |

### Paso 4 — Zoom acercar (si expuesto)
| | |
|---|---|
| **Act** | `invoke_element(name="Ver")` |
| **Act** | `list_elements(role="MenuItem", max_depth=3)` → Acercar/Alejar |
| **Act** | invoke Acercar (si existe) |
| **Verify A** | Text status ≠ 100% (ej. 110% o 125%) |
| **Verify B** | screenshot diferencia visual |

### Paso 5 — Zoom restablecer
| | |
|---|---|
| **Act** | invoke Restablecer zoom o Alejar hasta 100% |
| **Verify** | Text `100%` |

### Paso 6 — Hito
| | |
|---|---|
| **Act** | `screenshot(scope="window")` |
| **Verify** | Barra visible 100% |

## Checkpoints

| CP | Gate |
|----|------|
| CP-1 | 1025 + Text hijos baseline |
| CP-2 | Toggle off verify element_exists fail |
| CP-3 | Toggle on restore |
| CP-4 | Zoom cambia porcentaje Text |

## Referencias

- [NP-09-statusbar.md](NP-09-statusbar.md)

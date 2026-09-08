# NP-21 — Pre-flight sesión (health check completo)

**Estado:** met (2026-09-06)  
**Última verificación:** —  
**Tools MCP:** `check_version`, `check_session_status`, `launch_app`, `set_target_window`, `get_target_window`, `detect_framework`, `detection_health`, `list_windows`, `list_elements`, `read_element`, `element_exists`, `get_focused_element`, `screenshot`  
**Recovery típico:** L3 si `target_alive=false`

## Objetivo

Validar que la sesión MCP + Notepad están listos **antes** de cualquier flujo NP. Cada checkpoint es gate: no continuar harness si alguno falla.

## Precondiciones

- [ ] MCP `awdui` conectado (`check_version`)
- [ ] Sin otros harness GUI en background (`AWDUI_GUI_SESSION` no activo)

## Pasos

### Paso 0 — MCP vivo
| | |
|---|---|
| **Act** | `check_version` |
| **Verify A** | `status: up to date` |
| **Verify B** | `check_session_status` → `operations_available` incluye `uia_find=true` |
| **Si falla** | Reiniciar MCP (`scripts/restart-awdui-mcp.ps1`) → repetir paso 0 |

### Paso 1 — Baseline escritorio
| | |
|---|---|
| **Act** | `list_windows` |
| **Verify A** | Anotar conteo total y títulos con `notepad.exe` |
| **Verify B** | 0 modales `#32770` huérfanos de sesiones previas (Buscar, Guardar como, Abrir) |
| **Si falla** | L1: `focus_window` modal + Cancelar + `list_windows` limpio |

### Paso 2 — Lanzar / reutilizar Notepad
| | |
|---|---|
| **Act** | `launch_app(path="notepad.exe", reuse=true)` |
| **Verify A** | Respuesta `Reused` o `Launched` con PID |
| **Verify B** | `list_windows` → título contiene `Bloc de notas` |
| **Timing** | Anotar ms; >3000ms → flag slow en evidencia |

### Paso 3 — Target MCP
| | |
|---|---|
| **Act** | `set_target_window(title="Bloc de notas", focus_policy="minimal")` |
| **Verify A** | `get_target_window` → `Bloc de notas`, `focus_policy=minimal` |
| **Verify B** | `check_session_status` → `target_alive=true` (si false → L3) |

### Paso 4 — Framework
| | |
|---|---|
| **Act** | `detect_framework(window_title="Bloc de notas")` |
| **Verify A** | `framework=win32` |
| **Act** | `detection_health` |
| **Verify B** | backends recomendados incluyen `flaui` o `uia` OK |

### Paso 5 — Árbol mínimo accionable
| | |
|---|---|
| **Act** | `list_elements(role="MenuItem", max_depth=4)` |
| **Verify A** | ≥5 MenuItem: Archivo, Edición, Formato, Ver, Ayuda |
| **Verify B** | Timing citado; si ≥3000ms documentar (propuesta list_elements slow) |
| **Act** | `element_exists(automation_id="15")` |
| **Verify C** | OK Document editor presente |

### Paso 6 — Editor vacío o seed mínimo
| | |
|---|---|
| **Act** | `read_element(automation_id="15")` |
| **Verify A** | Retorna `value` (vacío o texto previo — anotar) |
| **Act** | `set_element_value(automation_id="15", value="NP21_HEALTH_OK")` |
| **Verify B** | `read_element` id=15 contiene `NP21_HEALTH_OK` |
| **Verify C** | `get_focused_element` → role Document o Edit bajo Notepad |

### Paso 7 — Status bar baseline
| | |
|---|---|
| **Act** | `list_elements(role="Text", max_depth=6)` filtrar hijos StatusBar |
| **Verify A** | Texto contiene `Línea` y `columna` |
| **Verify B** | Texto contiene `UTF-8` y `CRLF` (Win11 ES) |

### Paso 8 — Hito screenshot
| | |
|---|---|
| **Act** | `screenshot(scope="window", window_title="Bloc de notas")` |
| **Verify** | Archivo PNG citado; editor muestra `NP21_HEALTH_OK` |

### Paso 9 — Cierre pre-flight
| | |
|---|---|
| **Verify** | `list_windows` sin modales nuevos |
| **Nota** | No llamar `set_target_window("")` si siguen flujos NP en el mismo turno |

## Matriz de checkpoints (resumen)

| CP | Gate | Tool verify |
|----|------|-------------|
| CP-0 | MCP up | check_version + check_session_status |
| CP-1 | Escritorio limpio | list_windows sin #32770 stale |
| CP-2 | Proceso vivo | launch_app + list_windows |
| CP-3 | Target scope | get_target_window + target_alive |
| CP-4 | Framework win32 | detect_framework + detection_health |
| CP-5 | Menú + editor | list_elements MenuItem + element_exists 15 |
| CP-6 | ValuePattern | read_element + set + read |
| CP-7 | Status bar | list_elements Text UTF-8/CRLF |
| CP-8 | Evidencia visual | screenshot |

## Evidencia registrada

| Campo | Valor |
|-------|-------|
| timing_ms | (por paso) |
| notepad_matrix | pending → met |
| notas | Pre-requisito recomendado antes de NP-22..NP-30 |

## Referencias

- [protocol/agentic-execution.md](../protocol/agentic-execution.md)
- [SKILL.md](../SKILL.md) § Inicio de sesión

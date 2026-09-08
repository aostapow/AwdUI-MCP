# NP-26 — Nueva ventana + aislamiento scope

**Estado:** met  
**Tools MCP:** `launch_app`, `list_windows`, `invoke_element`, `list_elements`, `set_element_value`, `read_element`, `set_target_window`, `get_target_window`, `get_all_values`, `screenshot`  
**Recovery típico:** L3 si ventanas duplicadas confusas

## Objetivo

Abrir **Nueva ventana** (Archivo id=8), verificar **dos** instancias Notepad, escribir texto distinto en cada una sin leak de scope.

## Pasos

### Paso 0 — Baseline
| | |
|---|---|
| **Act** | `list_windows` |
| **Verify A** | Contar ventanas `notepad.exe` = N (anotar) |
| **Verify B** | 0 modales #32770 |

### Paso 1 — Seed ventana A
| | |
|---|---|
| **Act** | `set_target_window("Bloc de notas")` |
| **Act** | `set_element_value(id=15, value="WINDOW_A_MARKER")` |
| **Verify** | read_element contiene WINDOW_A_MARKER |

### Paso 2 — Abrir nueva ventana
| | |
|---|---|
| **Act** | `invoke_element(name="Archivo")` |
| **Act** | `invoke_element(automation_id="8")` |
| **Verify A** | `list_windows` → **N+1** ventanas notepad.exe |
| **Verify B** | Nueva ventana título `Sin título: Bloc de notas` (segunda instancia) |

### Paso 3 — Target ventana B
| | |
|---|---|
| **Act** | Identificar HWND/título segunda ventana en list_windows |
| **Act** | `set_target_window` con título exacto segunda ventana |
| **Verify A** | get_target_window apunta ventana B |
| **Act** | `read_element(id=15)` |
| **Verify B** | Value **vacío** o distinto de WINDOW_A_MARKER |

### Paso 4 — Seed ventana B
| | |
|---|---|
| **Act** | `set_element_value(id=15, value="WINDOW_B_MARKER")` |
| **Verify** | read_element WINDOW_B_MARKER |

### Paso 5 — Volver ventana A
| | |
|---|---|
| **Act** | `set_target_window` primera ventana (título con WINDOW_A o primera en list) |
| **Verify A** | read_element sigue WINDOW_A_MARKER |
| **Verify B** | read_element **no** contiene WINDOW_B_MARKER |

### Paso 6 — Scope leak check
| | |
|---|---|
| **Act** | `get_all_values(scope="auto")` |
| **Verify A** | Solo Document(s) de ventana target actual |
| **Verify B** | No leak Units1/Calculadora si Calc abierta |

### Paso 7 — Cerrar ventana B
| | |
|---|---|
| **Act** | `set_target_window` ventana B |
| **Act** | `send_keys("alt+f4")` |
| **Verify A** | list_windows → N ventanas notepad (vuelve a inicial) |
| **Verify B** | Ventana A aún tiene WINDOW_A_MARKER |

### Paso 8 — Hito
| | |
|---|---|
| **Act** | `screenshot` ventana A |
| **Act** | `set_target_window("Bloc de notas")` |

## Checkpoints

| CP | Gate |
|----|------|
| CP-2 | +1 ventana notepad |
| CP-3 | Ventana B editor vacío al abrir |
| CP-5 | A y B valores aislados |
| CP-6 | get_all_values sin cross-window leak |

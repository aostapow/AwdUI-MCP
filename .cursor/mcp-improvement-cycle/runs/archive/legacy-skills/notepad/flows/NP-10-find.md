# NP-10 — Buscar + F3 (Win11 ES)

**Estado:** met (2026-09-06)  
**Tools MCP:** `list_windows`, `focus_window`, `read_element`, `type_text`, `invoke_element`, `list_elements`, `set_element_value`, `click_element`, `send_keys`, `screenshot`  
**Recovery típico:** L1 cierre modal `Buscar` — verify con `list_windows`, no confiar solo en verify MCP

## Descubrimiento Win11 ES (crítico)

| Atajo documentado | Real Win11 ES Notepad |
|-------------------|----------------------|
| Ctrl+F → Buscar | **Ctrl+F → Búsqueda con Bing** (MenuItem id=28) |
| Ctrl+H → Reemplazar | **Ctrl+R → Reemplazar** (MenuItem id=23) |
| — | **Ctrl+B → Buscar...** (MenuItem id=21) → modal `#32770` |

**No es panel inline** en esta build: `invoke_element(Edición)` → `Buscar...` id=21 abre ventana `Buscar` #32770.

## Precondiciones

- [ ] Baseline L0: 0 modales `#32770`
- [ ] `launch_app` + `set_target_window("Bloc de notas")`
- [ ] Texto seed en editor (paso 2)

## Pasos

### Paso 0 — Baseline
| | |
|---|---|
| **Act** | `list_windows` |
| **Verify** | Sin modales notepad; Notepad presente |

### Paso 1 — Enfocar
| | |
|---|---|
| **Act** | `focus_window("Bloc de notas")` |
| **Verify** | `get_focused_element` → Editor id=15 |

### Paso 2 — Seed
| | |
|---|---|
| **Act** | `type_text("find alpha beta gamma\nfind alpha here\nfind beta there\ngamma line")` |
| **Verify** | `read_element` id=15 contiene `find alpha here` |

### Paso 3 — Abrir Buscar (menú, no Ctrl+F)
| | |
|---|---|
| **Act** | `invoke_element(name="Edición")` |
| **Act** | `list_elements(role="MenuItem", max_depth=2)` → confirmar id=21 |
| **Act** | `invoke_element(automation_id="21")` |
| **Verify A** | `list_windows` → `Buscar [#32770/notepad.exe]` |
| **Verify B** | `get_focused_element` → Edit `"Buscar:"` id=1152 |

### Paso 4 — Término
| | |
|---|---|
| **Act** | `set_element_value(automation_id="1152", value="alpha", window_title="Buscar")` |
| **Verify** | ValuePattern OK |

### Paso 5 — Buscar siguiente
| | |
|---|---|
| **Act** | `click_element(automation_id="1", window_title="Buscar")` |
| **Verify** | click verified; status bar Notepad cambia (ej. Línea 4, col 16) |
| **Nota** | `invoke_element` id=1 puede stale; preferir `click_element` |

### Paso 6 — Cerrar modal
| | |
|---|---|
| **Act** | `click_element(automation_id="2", window_title="Buscar")` |
| **Verify** | `list_windows` → **sin** `Buscar` (Escape/invoke verify MCP no basta) |

### Paso 7 — Hito
| | |
|---|---|
| **Act** | `screenshot(scope="window", window_title="Bloc de notas")` |

## Evidencia 2026-09-06

- Seed read_element OK 4 líneas
- Modal Buscar #32770; Edit Buscar: id=1152
- click_element Buscar siguiente id=1 ✓ verified
- Cierre: click Cancelar id=2 + list_windows 9 ventanas sin Buscar

## Referencias

- [modals/find-replace.md](../modals/find-replace.md)
- [protocol/recovery.md](../protocol/recovery.md)

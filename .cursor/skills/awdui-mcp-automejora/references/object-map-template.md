# Template — Mapa de objetos UI

Completar durante Fase 4. Copiar y rellenar por flujo.

```markdown
# Flujo: <nombre del flujo>
Fecha: <YYYY-MM-DD>
App: <nombre proceso / exe>
Ventana: <título parcial para set_target_window>

## 0. Diagnóstico
- Framework: <detect_framework>
- Backends OK: <detection_health>
- Fingerprint inicial: <ui_fingerprint>
- Notas: <modales, permisos, JAB, Electron flag, etc.>

## 1. Ventana
| Campo | Valor |
|-------|-------|
| title_match | |
| role | Window / Dialog |
| automation_id | |
| backend | |

## 2. Objetos padre (contenedores)

### PADRE-1: <nombre lógico>
| Campo | Valor |
|-------|-------|
| role | MenuBar / TabControl / Pane / Group / ... |
| name | |
| automation_id | |
| class_name | |
| backend | |
| visible_sin_probe | sí / no |
| probe_usado | <si aplica: expand_menu, select_tab, ...> |

### PADRE-2: ...
(repetir)

## 3. Objetos hijo (controles del flujo)

### OBJ-1: <nombre lógico>
| Campo | Valor |
|-------|-------|
| paso_flujo | <qué hace el usuario> |
| padre | PADRE-N |
| role | Button / Edit / ComboBox / MenuItem / ... |
| name | |
| automation_id | |
| class_name | |
| localizador_primario | |
| localizador_fallback | |
| backend_validado | |
| highlight_ok | sí / no |

### OBJ-2: ...
(repetir)

## 4. Secuencia de reproducción

| # | Acción | Objeto | Tool | Verificación |
|---|--------|--------|------|--------------|
| 1 | | OBJ-1 | click_element | ui_fingerprint / screenshot |
| 2 | | OBJ-2 | set_element_value | get_focused_element |
| 3 | | | send_keys | wait_for_change |

## 5. Riesgos y fallbacks
- <elemento frágil>: usar OCR `find_text("...")` o repo_path `...`
- <pantalla modal>: esperar con start_watcher / observe_ui_tool
```

## Criterios de localizador

| Prioridad | Criterio | Ejemplo |
|-----------|----------|---------|
| 1 | automation_id único en el padre | `automation_id="btnSave"` |
| 2 | name + role | `name="Guardar" role="Button"` |
| 3 | name + role + class_name | para WinForms owner-draw |
| 4 | repo_path | `frmMain/btnSave` |
| 5 | OCR text | `find_text("Guardar")` |
| 6 | template image | `find_by_template_tool` |
| 7 | coordenadas | solo último recurso, documentar región |

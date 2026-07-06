# Ejemplo — Guardar archivo en Notepad

Flujo del usuario: *Abrir Notepad → escribir texto → Archivo → Guardar como → elegir ruta → Guardar*

## Fase 0 — Ventana

```
list_windows                          → identificar "Sin título - Notepad"
set_target_window("Notepad")
get_target_window                       → confirmar
```

## Fase 1 — Shell

```
detect_framework(window_title="Notepad")     → win32 / winforms
detection_health(window_title="Notepad")     → uia: OK, flaui: OK
observe_ui_tool(window_title="Notepad")      → MenuBar visible, fingerprint abc123
```

## Fase 2 — Padres

```
list_elements(window_title="Notepad", max_depth=2)
```

Resultado esperado (ejemplo):

| Padre lógico | role | name |
|--------------|------|------|
| MAIN-WIN | Window | Sin título - Notepad |
| MENU | MenuBar | Sistema |
| EDITOR | Document | (área de texto) |

```
spy_tree(window_title="Notepad", max_depth=3)   → confirmar jerarquía
```

## Fase 3 — Hijos del flujo

Dentro de MENU:

```
list_elements(window_title="Notepad", role="MenuItem", max_depth=4)
```

| Objeto | role | name | automation_id |
|--------|------|------|---------------|
| OBJ-MENU-FILE | MenuItem | Archivo | |
| OBJ-MENU-SAVEAS | MenuItem | Guardar como | |

Validar cada uno:

```
smart_find(name="Archivo", role="MenuItem", window_title="Notepad", highlight=true)
```

Si "Guardar como" no está visible hasta expandir menú:

```
plan_probes_tool(goal="Guardar como", window_title="Notepad", hints="Archivo")
apply_probe_tool(probe_id="expand_menu", target="Archivo", window_title="Notepad")
list_elements(...)   → re-listar hijos bajo Archivo
```

## Fase 4 — Mapa (extracto)

```
PASO 1: Abrir menú Archivo    → OBJ-MENU-FILE   → click_element(name="Archivo", role="MenuItem")
PASO 2: Elegir Guardar como   → OBJ-MENU-SAVEAS → click_element(name="Guardar como", role="MenuItem")
PASO 3: Diálogo Guardar       → PADRE-DIALOG    → nueva ventana "Guardar como"
PASO 4: Campo nombre archivo  → OBJ-FILENAME    → set_element_value / Edit
PASO 5: Botón Guardar         → OBJ-BTN-SAVE    → click_element(name="Guardar", role="Button")
```

## Fase 5 — Validación

```
smart_find(name="Archivo", role="MenuItem", window_title="Notepad", highlight=true)
ui_fingerprint(window_title="Notepad")   → antes
click_element(name="Archivo", role="MenuItem", window_title="Notepad")
ui_fingerprint(window_title="Notepad")   → debe cambiar
```

## Fase 6 — Reproducción

```
set_target_window("Notepad")
click_element(name="Archivo", role="MenuItem", window_title="Notepad")
click_element(name="Guardar como", role="MenuItem", window_title="Notepad")
set_target_window("Guardar como")          → cambiar target al diálogo modal
set_element_value(name="Nombre:", text="informe.txt", window_title="Guardar como")
click_element(name="Guardar", role="Button", window_title="Guardar como")
screenshot()                               → verificar archivo guardado
focus_window(title="Claude")
```

## Variante — app opaca (sin árbol útil)

Si `detection_health` muestra pocos elementos:

```
detect_visual_regions(window_title="MiApp")
build_detection_context(name="Guardar", window_title="MiApp")
find_text("Guardar")
click_text("Guardar")
```

Documentar en el mapa que el backend primario es OCR/visual, no UIA.

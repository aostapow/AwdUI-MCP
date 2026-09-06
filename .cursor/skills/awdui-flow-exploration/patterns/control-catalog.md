# Catálogo de controles UIA — tipos, patterns e interacción

Guía **genérica** basada en los [40 tipos de control UIA](https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-controltype-ids) y el [mapeo oficial control → patterns](https://learn.microsoft.com/en-us/dotnet/framework/ui-automation/control-pattern-mapping-for-ui-automation-clients).

**Flujo obligatorio en Fase 3:**

1. `spy_inspect(automation_id=…)` → `role` + `patterns`
2. Buscar el **Control Type** en la tabla de abajo
3. **Leer** valores/opciones con el método indicado
4. **Interactuar** con la tool AwdUI indicada
5. **Verificar** efecto (UIA poll, no solo screenshot) — ver sección *Espera y verificación*
6. OCR solo si la columna «OCR» aplica

Referencias: [control-patterns-reference.md](control-patterns-reference.md) (todos los patterns) · [winforms.md](winforms.md) (combos, lookup, MDI) · mapa machine-readable: `mcp-servers/awdui-server/detection/data/uia_control_map.json` (sincronizado con Microsoft; usado por `discover_control_interaction`).

---

## Árbol de decisión por patterns (más fiable que solo el role)

```
spy_inspect → patterns presentes:
  Selection + ExpandCollapse     → ComboBox / List → list_control_items → select_control_item
  Grid + Table (+ DataItem hijos)→ Table / DataGrid → list_control_items / select_lookup_row
  Invoke                         → Button / MenuItem / Hyperlink → invoke_element
  Value (sin RangeValue)         → Edit / Combo editable → set_element_value
  RangeValue                     → Slider / ScrollBar / ProgressBar → invoke_pattern(RangeValue) o set_element_value
  Toggle                         → CheckBox / ítem checkeable → invoke_pattern(Toggle) o invoke_element
  ExpandCollapse (sin Invoke)    → TreeItem / menú → invoke_pattern(ExpandCollapse) → listar hijos
  SelectionItem en hijo          → ListItem / TreeItem / fila → select_control_item / invoke_pattern
  Scroll en contenedor           → List/Tree/Grid virtual → scroll_element (ScrollPattern)
  Text                           → Document / área rich text → set_element_value / get_control_state(Text)
  (ninguno útil)                 → Custom / Image → smart_find → OCR último recurso
```

---

## Tabla completa por Control Type

Leyenda: **S** = pattern soportado siempre · **C** = condicional · **—** = no aplica  
**Leer** = cómo obtener estado/opciones · **Actuar** = interacción preferida · **Tools** = AwdUI

### Entrada de datos y selección

| Control Type | Patterns (S / C) | Leer | Actuar | Tools AwdUI | OCR |
|--------------|------------------|------|--------|-------------|-----|
| **ComboBox** | C: ExpandCollapse, Selection, Value | `list_control_items` (expande combo) | `select_control_item`; editable: `set_element_value`; lookup: modal | `list_control_items`, `select_control_item`, `set_element_value` | No si lista OK |
| **Edit** | C: Value, Text, RangeValue | `get_element_properties` → value | `set_element_value`; fallback foco+`type_text` | `set_element_value`, `click`+`type_text` | No |
| **Document** | S: Text · C: Scroll, Value | TextPattern / value | `set_element_value`, clipboard+pegar | `set_element_value`, `clipboard` | Solo si sin Text |
| **List** | C: Grid, MultipleView, Scroll, Selection | `list_control_items` en el List | `select_control_item` en ítem | `list_control_items`, `select_control_item` | No |
| **ListItem** | S: SelectionItem · C: Invoke, ExpandCollapse, GridItem, Toggle, Value | name + value de celda | `select_control_item`; o `invoke_element` si es botón | `select_control_item`, `invoke_element` | No |
| **Spinner** | C: RangeValue, Selection, Value | properties value/min/max | `set_element_value` o flechas `send_keys` | `set_element_value`, `send_keys` | No |
| **Slider** | C: RangeValue, Selection, Value | value actual en properties | `set_element_value` si disponible | `set_element_value` | No |
| **ScrollBar** | C: RangeValue | posición | `send_keys` / drag thumb | `scroll`, `send_keys` | No |
| **Calendar** | S: Grid, Table · C: Selection, Scroll | celdas fecha en grid | click celda / `select_control_item` | `list_control_items`, `click_element` | No |
| **CheckBox** | S: Toggle | ToggleState | `invoke_element` (toggle) | `invoke_element` | No |
| **RadioButton** | S: SelectionItem | IsSelected | `select_control_item` o click grupo | `select_control_item`, `click_element` | No |

### Tablas y grillas

| Control Type | Patterns (S / C) | Leer | Actuar | Tools AwdUI | OCR |
|--------------|------------------|------|--------|-------------|-----|
| **Table** | S: Grid, GridItem, Table, TableItem | Celdas `DataItem`; DevExpress: valor en Value/LegacyIAccessible, name=`col row N` | `select_lookup_row` (doble click lookup); click fila | `list_control_items`, `select_lookup_row` | **No** si celdas UIA |
| **DataGrid** | S: Grid · C: Scroll, Selection, Table | idem Table | idem Table | idem | **No** |
| **DataItem** | S: SelectionItem · C: GridItem, TableItem, Value, Toggle… | **Siempre** leer Value/LegacyIAccessible, no solo name | Agrupar bajo grid padre; no clicar celda suelta | `spy_inspect`, grid tools | No |
| **Header** / **HeaderItem** | C: Transform, Invoke | textos columna | raramente interactuar | `list_elements` | No |

### Botones y comandos

| Control Type | Patterns (S / C) | Leer | Actuar | Tools AwdUI | OCR |
|--------------|------------------|------|--------|-------------|-----|
| **Button** | C: Invoke, Toggle, ExpandCollapse | name / automation_id | **`invoke_element`**; fallback `click` coords | `invoke_element`, `click_element`, `click` | No |
| **SplitButton** | S: Invoke, ExpandCollapse | name | Invoke parte principal; Expand menú desplegable | `invoke_element`, luego list hijos | No |
| **Hyperlink** | S: Invoke · C: Value | name + URL value | `invoke_element` | `invoke_element` | No |
| **Thumb** | S: Transform | posición | drag (scroll pane) | `drag` | No |

### Menús y barras

| Control Type | Patterns (S / C) | Leer | Actuar | Tools AwdUI | OCR |
|--------------|------------------|------|--------|-------------|-----|
| **MenuBar** | C: ExpandCollapse, Dock, Transform | hijos MenuItem | expandir / navegar teclado | `list_elements(role=MenuItem)` | No |
| **Menu** | — | hijos MenuItem | — (contenedor) | `list_elements` | No |
| **MenuItem** | C: Invoke, ExpandCollapse, SelectionItem, Toggle | name | Invoke=ejecutar; Expand=submenú; Toggle=check | `invoke_element`, `apply_probe_tool` | No |
| **ToolBar** | C: Dock, ExpandCollapse, Transform | hijos Button | `invoke_element` en hijo | `list_elements(role=Button)` | No |
| **AppBar** | (Win 8.1+) similar toolbar | hijos | invoke hijos | `list_elements` | No |
| **StatusBar** | C: Grid | paneles estado | leer texto hijos | `list_elements` | No |

### Pestañas y árbol

| Control Type | Patterns (S / C) | Leer | Actuar | Tools AwdUI | OCR |
|--------------|------------------|------|--------|-------------|-----|
| **Tab** | S: Selection · C: Scroll | hijos TabItem | — (contenedor) | `list_elements(role=TabItem)` | No |
| **TabItem** | S: SelectionItem | name, IsSelected | `invoke_element` / `click_element` | `invoke_element`, `click_element` | No |
| **Tree** | C: Scroll, Selection | hijos TreeItem (tras expand) | — (contenedor) | `list_elements(role=TreeItem)` | No |
| **TreeItem** | S: ExpandCollapse · C: Invoke, SelectionItem, Toggle | name; expandir si tiene hijos | Expand → `select_control_item` o Invoke | `apply_probe_tool`, `select_control_item` | No |

### Contenedores y estructura (mapear, no clicar)

| Control Type | Patterns | Uso en exploración |
|--------------|----------|-------------------|
| **Window** | C: Transform, Window | `set_target_window`; scope con `window_title` |
| **Pane** | C: Dock, Scroll, Transform | Contenedor — Fase 2; buscar hijos |
| **Group** | C: ExpandCollapse | Agrupación visual — listar hijos |
| **Custom** | variable | `spy_inspect`; si vacío → smart_find / OCR |
| **Separator** | — | Ignorar |
| **ToolTip** | C: Text, Window | Leer texto; no interactuar |
| **TitleBar** | — | Sistema; evitar |
| **Image** | C: GridItem, TableItem | Decoración; OCR/template si clic necesario |
| **Text** | C: GridItem, TableItem, Text | Etiqueta estática — leer name; no editar |
| **ProgressBar** | C: RangeValue, Value | Solo lectura de progreso |
| **SemanticZoom** | (Win 8.1+) | Cambio vista zoom — invoke/expand |

---

## Resumen por intención del agente

| Quiero… | Control types típicos | Secuencia |
|---------|----------------------|-----------|
| Elegir opción en lista desplegable | ComboBox, List | `list_control_items` → `select_control_item` |
| Elegir fila en grilla | Table, DataGrid | `list_control_items(filter)` → `select_lookup_row` |
| Pulsar acción | Button, MenuItem, Hyperlink | `invoke_element` |
| Escribir texto | Edit, Document, Combo editable | `set_element_value` |
| Marcar / desmarcar | CheckBox, MenuItem+Toggle | `invoke_pattern(Toggle)` o `invoke_element` |
| Elegir una de varias opciones | RadioButton | `select_control_item` o `invoke_pattern(SelectionItem)` |
| Cambiar pestaña | TabItem | `invoke_element` |
| Navegar árbol | TreeItem | `invoke_pattern(expand)` → hijo → `select_control_item` |
| Ajustar valor numérico | Slider, Spinner, ScrollBar | `invoke_pattern(RangeValue)` o `set_element_value` |
| Leer estado de control | cualquiera | `get_control_state` |
| Scroll en grilla/lista virtual | Table, List, Tree | `scroll_element` + `list_control_items` |
| Fila de grilla por índice | Table, DataGrid | `get_grid_item(row, column)` o `select_control_item` |
| Grilla completa (JSON) | Table, DataGrid | `read_table` |
| Formulario completo | Edit, ComboBox | `fill_form`, `get_all_values` |
| Duplicados en árbol | Button, DataItem | `find_all_elements` → `click_element(index=N)` |
| Modal lookup (HWND) | Window hijo | `get_snapshot(window_handle=…)` → `set_element_value` / `click_element` |
| Async UI update | cualquiera | `start_event_monitor` → `get_event_log` |
| Buscar control desconocido | Custom, Image | `smart_find` → OCR si falla |
| Confirmar efecto tras actuar | cualquiera | `invoke_element` / `click_element` con `verify_*` (preferido) |
| Solo esperar (sin actuar) | cualquiera | `wait_for_element` / `wait_for_condition` |
| ¿Existe control ahora? | cualquiera | `element_exists` |
| Sesión / caché stale | Window | `check_session_status`, `invalidate_cache` |
| App lista tras launch | Window | `wait_for_input_idle` |

---

## Espera y verificación (act + wait tools)

AwdUI tiene **dos capas** (no excluyentes):

| Capa | Tools | Cuándo |
|------|-------|--------|
| **Integrada** | `verify_automation_id`, `verify_name_contains` en `invoke_element` / `click_element` | Caso habitual: pulsás botón y verificás display/estado en **la misma llamada** (poll UIA, default 5s) |
| **Separada** | `wait_for_condition`, `wait_for_element`, `wait_for_input_idle` | Sin actuar; esperar diálogo/carga; verify de un paso **anterior**; timeout distinto |

**Preferir integrado** cuando actuás y el resultado es un `name`/`value` en otro control:

```
invoke_element(
  automation_id="equalButton",
  verify_automation_id="CalculatorResults",
  verify_name_contains="Se muestra 7"
)
```

**Usar wait tool separada** cuando:

- Tras `launch_app` → `wait_for_input_idle`
- Abrís flyout/modal y solo querés ver que apareció `LightDismiss` (sin otro invoke)
- El verify es de un paso previo, no del act actual
- Necesitás `verify_timeout_ms` / `verify_poll_ms` explícitos en un wait aislado

Propiedades en `wait_for_condition`: `name`, `isEnabled`, `visible`, `text`, `value`, `isChecked`, `isSelected`.

**Último recurso visual:** `wait_for_change` (diff de píxeles) — solo si UIA no alcanza.

**Display en otra app:** si el botón actuado no es el display, pasar `verify_automation_id` explícito o `agent_hints` en repo (`verify_automation_id: …` en el objeto actuado).

---

## Casos que confunden (WinForms / DevExpress)

| Lo que ves en UIA | Qué es realmente | Qué hacer |
|-------------------|------------------|-----------|
| `DataItem` `"titulo row 0"` | Celda de grilla, valor en **Value** | `select_lookup_row`, no OCR |
| ComboBox sin hijos en árbol | Items solo al expandir | `list_control_items(expand=true)` |
| ComboBox + botón lupa | Lookup modal | Filtrar en modal → grid → `select_lookup_row` |
| `Button` sin Invoke | WinForms legacy | `click` en centro UIA |
| Ventana hija MDI | Mismo proceso, otro HWND | `set_target_window` padre; scope automático |
| Lista virtualizada larga | VirtualizedItem | `scroll_element` → `realize_virtualized_item` → `list_control_items` |

---

## Cobertura MCP (patterns → tools)

| Pattern UIA | Leer estado | Actuar | Tool AwdUI |
|-------------|-------------|--------|------------|
| Invoke | `get_control_state` | invoke | `invoke_element`, `invoke_pattern` |
| Toggle | toggle_state | on/off/toggle | `invoke_pattern(Toggle)` |
| ExpandCollapse | expand_state | expand/collapse | `invoke_pattern(ExpandCollapse)`, `repo_action` |
| Value | value, is_read_only | set | `set_element_value`, `invoke_pattern(Value)` |
| RangeValue | min/max/value | set | `invoke_pattern(RangeValue)`, `set_element_value` (fallback) |
| Scroll | scroll %, view size | scroll/set_percent | `scroll_element` |
| ScrollItem | — | scroll_into_view | `scroll_into_view` |
| SelectionItem | is_selected | select/add/remove | `select_control_item`, `invoke_element` |
| Selection | selected_count | get_selection | `discover_control_interaction`, `spy_inspect` |
| Text | text (DocumentRange) | read | `spy_inspect`, `get_element_properties` |
| VirtualizedItem | realizable | realize | `realize_virtualized_item` |
| ItemContainer | — | find by property | `find_item_by_property` |
| Grid/Table rows | cells via UIA | by value or index | `read_table`, `get_grid_item`, `select_control_item`, `select_lookup_row` |

**Resolución de ventana:** todas las tools de pattern usan `window_title` / `title` + fallback a `set_target_window` + scope MDI (`resolved_window_title` en respuesta).

---

## Cuándo usar OCR / visual

| Situación | Herramienta |
|-----------|-------------|
| `Custom` sin patterns ni hijos útiles | `smart_find` → `find_text` |
| Contenido web (browser page) | `find_text`, Tab, clipboard |
| Canvas / dibujo custom | `find_text`, `find_by_template_tool` |
| Icono sin name ni automation_id | template / OCR |
| Árbol UIA vacío (`detection_health`) | OCR como primario documentado |

## Cuándo NO usar OCR

- ComboBox con `list_control_items` exitoso
- Table/DataGrid con celdas `* row N` tras filtrar
- Cualquier control con `Value`/`LegacyIAccessible` legible
- Botón con `Invoke` en patterns

---

## Fuentes

- [UI Automation Control Types](https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-controltypesoverview)
- [Control Pattern Mapping (clientes)](https://learn.microsoft.com/en-us/dotnet/framework/ui-automation/control-pattern-mapping-for-ui-automation-clients)
- [Control Patterns Overview](https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-controlpatternsoverview)

# Referencia UIA — Control Patterns (Microsoft)

Fuente: [UI Automation Control Patterns Overview](https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-controlpatternsoverview) y [Control Pattern Mapping](https://learn.microsoft.com/en-us/dotnet/framework/ui-automation/control-pattern-mapping-for-ui-automation-clients).

Los patterns se **combinan** en un mismo elemento. `spy_inspect` lista cuáles soporta cada control.

| Pattern | Qué expone | Lectura (cliente) | Acción (cliente) | Tool AwdUI |
|---------|------------|-------------------|------------------|------------|
| **Invoke** | Acción única sin estado | — | `.Invoke()` | `invoke_element` |
| **Value** | Valor string (sin rango) | `.CurrentValue` | `.SetValue(text)` | `get_element_properties`, `set_element_value` |
| **RangeValue** | Valor numérico en rango | Value, Min, Max, LargeChange | `.SetValue(n)` | `set_element_value` (si expone Value) |
| **Toggle** | On / Off / indeterminado | `.ToggleState` | `.Toggle()` | `invoke_element` |
| **Selection** | Contenedor con selección | `CurrentSelection`, `CanSelectMultiple` | — | `list_control_items` en el contenedor |
| **SelectionItem** | Ítem seleccionable | `.IsSelected` | `.Select()`, `.AddToSelection()` | `select_control_item` |
| **ExpandCollapse** | Expandido / colapsado | `.ExpandCollapseState` | `.Expand()`, `.Collapse()` | expand vía `list_control_items(expand=true)` |
| **Scroll** | Área con scroll | Horizontal/Vertical scroll % | `.Scroll(…)`, `.SetScrollPercent` | `scroll`, `send_keys` PgDn |
| **ScrollItem** | Ítem que debe hacer scroll into view | — | `.ScrollIntoView()` | implícito al seleccionar |
| **Grid** | Tabla con filas/columnas | RowCount, ColumnCount | `.GetItem(row,col)` | `list_control_items` / `grid_rows` |
| **GridItem** | Celda en grid | Row, Column, ContainingGrid | — | agrupar celdas por fila |
| **Table** | Grid + headers | RowHeaders, ColumnHeaders | — | `list_control_items` |
| **TableItem** | Celda con headers de fila/col | RowHeaderItems, ColumnHeaderItems | — | idem GridItem |
| **Text** | Texto estructurado (documentos) | TextPattern ranges | Select, Insert | `set_element_value`, clipboard |
| **TextEdit** | Edición programática de texto | — | — | `set_element_value` |
| **LegacyIAccessible** | Puente MSAA | `.Name`, `.Value`, `.Role` | varios | leído por `grid_rows`, properties |
| **Window** | Ventana top-level / modal | WindowVisualState, Modal | `.Close()`, `.SetVisualState` | `focus_window`, `set_target_window` |
| **Transform** | Move/resize/rotate | CanMove, CanResize | Move, Resize | raro en automatización formularios |
| **Dock** | Docking (toolbars) | DockPosition | SetDockPosition | manual / poco común |
| **MultipleView** | Vistas (iconos/lista/detalle) | CurrentView, GetSupportedViews | `.SetCurrentView` | `invoke_element` en selector vista |
| **VirtualizedItem** | Lista virtualizada | — | `.Realize()` | scroll + re-listar |
| **ItemContainer** | Búsqueda de ítem por propiedad | — | `.FindItemByProperty` | `find_element`, `smart_find` |
| **Drag** / **DropTarget** | Drag and drop | — | StartDrag / Drop | `drag` tool |
| **Annotation** | Comentarios en documento | — | — | raro |
| **Spreadsheet** / **SpreadsheetItem** | Hoja cálculo | Fórmulas, anotaciones | — | como Table + celdas |
| **SynchronizedInput** | Bloqueo input usuario | — | StartListening | no usar en automatización |
| **ObjectModel** | Modelo objeto subyacente | — | GetUnderlyingObjectModel | no expuesto en AwdUI |

## Regla de lectura de valor

Orden al leer texto de un control WinForms:

1. `Value` pattern → `CurrentValue`
2. `LegacyIAccessible` → `Value`
3. `name` property
4. `Text` pattern (documentos / edits largos)
5. OCR — **solo** si 1–4 vacíos o árbol inútil

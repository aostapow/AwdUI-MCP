# Patrones WinForms (cross-app)

Aplica a **cualquier** app WinForms con paneles anidados, combos y diálogos lookup.
Catálogo general de roles UIA: [control-catalog.md](control-catalog.md).

No incluye `automation_id` ni títulos de ventana de un producto concreto — eso va en la skill del producto.

## Combos (antes de OCR)

Tras mapear el panel del formulario (Fase 2):

1. `list_elements(role="ComboBox", max_depth=0, include_offscreen=true)` — o `max_depth=10` si el panel es muy profundo
2. Anotar `automation_id` de cada combo del flujo
3. `spy_inspect(automation_id=…)` — ver patterns (`Value`, `ExpandCollapse`)
4. Seleccionar:
   - **Dropdown simple:** `list_control_items` + `select_control_item` (o `win32_cb_setcursel` si verifica)
   - **Combo editable con filtro:** `list_control_items` devuelve `selection_via=click` y coords → **`click(x,y)`** (operación explícita, un solo click) → `get_control_state` verifica
   - Lookup modal (`btnBuscar`) solo si el combo no coopera
5. OCR solo si el paso 1 devuelve 0 combos en el panel objetivo

**No** usar `select_control_item` cuando la respuesta indica `requires_operation: click` — el popup ComboLBox requiere `click` como operación separada.

## Diálogos lookup (modal de búsqueda)

Cuando un combo tiene botón que abre un modal de búsqueda, aplica el [patrón de ventana activa](active-window.md): el diálogo es el sub-flujo hasta que cierre.

1. Tras abrir: `list_windows` — confirmar título del diálogo; **trabajar solo ahí** hasta cerrarlo
2. `list_elements(window_title=<título del diálogo>, role="Button"|"Edit")` — mapear campo de búsqueda, Filtrar y Aceptar
3. Tras filtrar: identificar contenedor del grid (`List`, `DataGrid`, `Table`) con `spy_inspect` o `list_elements` acotado al diálogo
4. `list_control_items(automation_id=<grid>, filter_text=<término buscado>)` — confirmar fila (lee valores de celda UIA en grillas DevExpress)
5. `select_lookup_row` o `select_control_item(..., double_click=true)` — **prohibido** `find_text`/`click_text` si el paso 4 puede resolver la fila
6. Si el diálogo no cierra con Enter: `invoke_element` en botón Aceptar/OK
7. **Salida obligatoria:** `list_windows` sin el diálogo (o foco de vuelta en el padre) antes de tocar controles del formulario principal
8. **Prohibido:** `list_elements(role=DataItem)` sin `window_title` del diálogo; click en fila 0; mezclar coordenadas OCR con bounds UIA de otro elemento; seguir en el padre con el modal abierto

**Preferir** selección directa en el combo (`discover_control_interaction` → `select_control_item` / `set_element_value`) antes de abrir lookup, salvo que el discovery indique que el combo no coopera.

## Ventanas hijas MDI / embebidas

- Fijar `set_target_window` a la ventana **principal** del proceso.
- Si `window_title` parcial no matchea un formulario hijo, el MCP resuelve ventanas del mismo proceso automáticamente.
- Para OCR/UIA scoped: usar el título parcial del formulario hijo; verificar `resolved_window_title` en la respuesta.

## Anti-patrones WinForms

- Asumir que `DataItem` índice 0 es el resultado de un filtro de búsqueda
- `click_text` en filas de grid cuando `list_control_items` devuelve el nombre esperado
- Doble click en coordenadas distintas al centro del `DataItem` listado sin `highlight_element`
- `list_elements(max_depth=5)` y concluir que no hay combos — escalar profundidad o filtrar por rol

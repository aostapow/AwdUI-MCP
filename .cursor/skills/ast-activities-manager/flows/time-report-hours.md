# Flujo — Carga de horas (Time Report)

## Precondiciones

- App abierta en `AST - Activities Manager`
- Usuario en módulo **Time Report** → pantalla **Carga de Horas**
- `set_target_window("AST")`

## Plantilla de carga (una fila)

Parámetros por fila:

| Parámetro | Ejemplo 1 | Ejemplo 2 |
|-----------|-----------|-----------|
| Término actividad | `accusys tf direccion` | `108082` |
| Horas | `2 hs, 0 min` | `6 hs, 0 min` |
| Grupo (substring) | `homologacion` | `homologacion` |
| Concepto (substring) | `calendario` | `calendario` |

### Pasos

```
1. highlight_element(btnBuscar) → click en centro de bbox (o click_element con automation_id)
2. set_element_value(teFind, <término>) en diálogo Buscar
   — fallback: click teFind + type_text
3. invoke_element(btFind, window_title="Buscar")
4. list_control_items(gcGrillaActividades, filter_text=<término>, window_title="Buscar")
   → confirmar fila esperada
5. select_lookup_row(gcGrillaActividades, value=<término>, dialog_title="Buscar")
6. set_element_value(cboHoras, "<N> hs, 0 min")
7. list_control_items(cboGrupo) → confirmar texto exacto de "homologacion"
8. select_control_item(cboGrupo, value="homologacion")
   → verificar: get_control_state(cboGrupo) value contiene "homologacion"
9. list_control_items(cboConcepto) → confirmar "calendario"
10. select_control_item(cboConcepto, value="calendario")
   → verificar: get_control_state(cboConcepto) value contiene "calendario"
11. spy_inspect(btnGuardar) → **is_enabled debe ser True**; si False, no guardar
12. highlight_element(btnGuardar) → click en esas coords (invoke suele fallar)
13. Verificar gcGrillaActividades o campos limpios post-guardado
```

### Atajos (menos pasos)

- Lookup grilla: tras `invoke(btFind)`, ir directo a `select_lookup_row` (no reintentar clics en btnBuscar).
- `btnBuscar`: **highlight_element** primero; click solo en coords del highlight.

### Errores a evitar

- `select_control_item` con `via set_value` en ComboBox dropdown = **no válido** (no habilita Guardar).
- `window_title="Buscar"` puede matchear Chrome — usar `AST` + scope MDI.

## Verificación

- Grid inferior muestra la actividad y horas cargadas
- `ui_fingerprint` o screenshot solo si hace falta confirmar visualmente

## Limpieza

```
set_target_window("")
```

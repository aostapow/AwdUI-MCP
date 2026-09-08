# Diálogo Fuente (#32770)

**Título UIA:** `Fuente` · **Clase:** `#32770`

| ID lógico | role | name | automation_id | tool |
|-----------|------|------|---------------|------|
| OBJ-FONT-LIST | List | Fuente: | 1000 | `list_control_items` + `select_control_item` |
| OBJ-FONT-SIZE | ComboBox | Tamaño: | — | `select_control_item` |
| OBJ-FONT-STYLE | RadioButton | Normal/Negrita/Cursiva | — | `select_control_item` |
| OBJ-FONT-OK | Button | Aceptar | 1 | `invoke_element` |
| OBJ-FONT-CANCEL | Button | Cancelar | 2 | `invoke_element` |

## Evidencia NP-08

- `list_control_items` id=1000 → matched=194, 6705ms ⚠ SLOW
- `select_control_item` value=Consolas → **OK** method=SelectionItem
- Menú: Formato → Fuente... id=33 (`invoke_element` 18s verify slow)

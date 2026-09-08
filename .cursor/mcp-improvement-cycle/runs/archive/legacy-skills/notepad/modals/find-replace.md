# Modal — Buscar / Reemplazar

## Identificación
| Diálogo | Título UIA (ES) |
|---------|-----------------|
| Buscar | `Buscar` |
| Reemplazar | `Reemplazar` |
| Atajo | Ctrl+F / Ctrl+H |

## Controles esperados (#32770)

| ID lógico | role | name (ES) | tool |
|-----------|------|-----------|------|
| OBJ-FIND-WHAT | Edit | Buscar qué: | fill_form, set_element_value |
| OBJ-FIND-REPLACE | Edit | Reemplazar con: | fill_form |
| OBJ-FIND-CASE | CheckBox | Coincidir mayúsculas y minúsculas | invoke_element |
| OBJ-FIND-WRAP | CheckBox | Envolver líneas | invoke_element |
| OBJ-FIND-NEXT | Button | Buscar siguiente | invoke_element |
| OBJ-FIND-CANCEL | Button | Cancelar | invoke_element |

## Secuencia modal
```
set_target_window("Buscar")
fill_form(...)
invoke_element(Buscar siguiente)
send_keys("escape")  → cerrar
set_target_window("Bloc de notas")
```

## Estado
pending mapeo UIA real

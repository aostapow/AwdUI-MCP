# Inventario UIA — Bloc de notas (verificado agenticamente)

**Sesión:** 2026-09-06 · Framework win32 · PID notepad.exe · DPI 1.25

## Ventana principal

```
Window "Sin título: Bloc de notas"
├── MenuBar (implícito en MenuItems top)
│   ├── MenuItem "Archivo"     (93,38)  64x24   patterns: Invoke, ExpandCollapse
│   ├── MenuItem "Edición"     (157,38) 63x24
│   ├── MenuItem "Formato"     (220,38) 70x24
│   ├── MenuItem "Ver"         (290,38) 35x24
│   └── MenuItem "Ayuda"       (325,38) 56x24
├── Document "Editor de texto" id=15     (93,63)  860x421  ValuePattern ✓
├── ScrollBar Vertical       id=NonClientVerticalScrollBar
│   ├── Button UpButton "Línea arriba"
│   └── Button DownButton "Línea abajo"
├── ScrollBar Horizontal     id=NonClientHorizontalScrollBar
└── StatusBar "Barra de estado" id=1025  (93,484) 860x29
    ├── Text "  Línea 1, columna 1"
    ├── Text " 100%"
    ├── Text " Windows (CRLF)"
    └── Text " UTF-8"
```

## Submenú Archivo (depth=5, menú abierto)

| # | role | name | automation_id | bbox |
|---|------|------|---------------|------|
| 0 | MenuItem | Nuevo Ctrl+N | 1 | (96,65) 315x24 |
| 1 | MenuItem | Nueva ventana Ctrl+Mayús+N | 8 | (96,89) |
| 2 | MenuItem | Abrir... Ctrl+A | 2 | (96,113) |
| 3 | MenuItem | Guardar Ctrl+G | 3 | (96,137) |
| 4 | MenuItem | Guardar como... Ctrl+Mayús+S | 4 | (96,161) |
| 5 | MenuItem | Configurar página... | 5 | (96,192) |
| 6 | MenuItem | Imprimir... Ctrl+P | 6 | (96,216) |
| 7 | MenuItem | Salir | 7 | (96,247) |

## Submenú Edición (menú abierto)

| # | role | name | automation_id | atajo |
|---|------|------|---------------|-------|
| 0 | MenuItem | Seleccionar todo | 25 | **Ctrl+E** (no Ctrl+A) |
| 1 | MenuItem | Buscar... | 21 | Ctrl+B |
| 2 | MenuItem | Reemplazar... | 23 | Ctrl+R |
| 3 | MenuItem | Ir a... | 24 | Ctrl+T |
| 4 | MenuItem | Hora y fecha | 26 | F5 |

**Quirk Win11 ES:** `Ctrl+A` = **Abrir** (Archivo id=2), no seleccionar todo.

## Diálogo Guardar como (#32770)

| ID lógico | role | name | automation_id | notas |
|-----------|------|------|---------------|-------|
| OBJ-SAVE-FILENAME | Edit | Nombre de archivo: | 1001 | ValuePattern |
| OBJ-SAVE-FILETYPE | ComboBox | Tipo: | FileTypeControlHost | |
| OBJ-SAVE-ENCODING | ComboBox | Codificación: | — | UTF-8 default |
| OBJ-SAVE-BTN | Button | Guardar | 1 | invoke OK, find SLOW |
| OBJ-SAVE-TREE | Tree | Vista en árbol | 100 | TreeItem Documentos, etc. |
| OBJ-SAVE-LIST | List | Vista Elementos | listview | ListItem carpetas |

**Scope leak observado:** Document id=15 del Notepad padre aparece en `list_elements` del diálogo.

## Patterns por rol (Notepad)

| Control Type | Objeto Notepad | Leer | Actuar | Tool AwdUI |
|--------------|----------------|------|--------|------------|
| Document | Editor id=15 | spy_inspect → Value | set_element_value | set_element_value, type_text |
| MenuItem | Archivo, Guardar como... | list tras expand | invoke_element | invoke_element |
| Button | Guardar (dialog) | find_element | invoke_element | invoke_element |
| Edit | Nombre archivo | get_element_properties | set_element_value, fill_form | fill_form |
| ComboBox | Tipo, Codificación | list_control_items | select_control_item | select_control_item |
| Tree / TreeItem | Navegación carpetas | list_elements | select_control_item | select_control_item |
| List / ListItem | Carpetas archivos | list_control_items | invoke_element | invoke_element |
| StatusBar + Text | Línea/col, UTF-8 | list_elements hijos | leer only | read via spy_inspect |
| CheckBox | Buscar (modal) | ToggleState | invoke_element | invoke_element |
| RadioButton | Fuente estilo | IsSelected | select_control_item | select_control_item |

## Diálogo Fuente (mapeado NP-08)

| role | name | automation_id |
|------|------|---------------|
| List | Fuente: | 1000 |
| Button | Aceptar | 1 |
| Button | Cancelar | 2 |

## Controles pendientes (NP-09..NP-14)

- Diálogo **Buscar**: Edit "Buscar qué", CheckBox "Coincidir mayúsculas"
- Diálogo **Reemplazar**: Edit buscar + reemplazar + botones
- Diálogo **Confirmar guardar**: Button "Guardar" / "No guardar" / "Cancelar"
- Menú contextual editor: clic derecho → Cut, Copy, Paste

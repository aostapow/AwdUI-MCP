# Modal — Guardar como

## Identificación
| Campo | Valor |
|-------|-------|
| Título UIA | `Guardar como` |
| Clase Win32 | `#32770` |
| Proceso | notepad.exe |
| Tamaño típico | 960x600 |

## Árbol UIA clave

```
Window "Guardar como"
├── Tree "Vista en árbol" id=100
│   └── TreeItem "Documentos", "Este equipo", ...
├── List "Vista Elementos" / ListItem carpetas
├── Edit "Nombre de archivo:" id=1001
├── ComboBox "Tipo:" id=FileTypeControlHost
├── ComboBox "Codificación:" (UTF-8 default)
└── Button "Guardar" id=1  (863,641) 88x26
```

## Interacción MCP

| Paso | Tool | Parámetros |
|------|------|------------|
| Target | set_target_window | `"Guardar como"` |
| Filename | fill_form | `fields_json=[{"automation_id":"1001","value":"archivo.txt"}]` |
| Tipo | select_control_item | ComboBox FileTypeControlHost |
| Carpeta | select_control_item | TreeItem "Documentos" |
| Guardar | invoke_element | `automation_id="1", name="Guardar", role="Button"` |
| Cancelar | invoke_element | Button "Cancelar" o send_keys escape |

## Watcher (NP-18)
```
start_watcher(poll_interval=1.0)
invoke_element(Guardar como...)
get_notifications(clear=true)  → debe listar ventana Guardar como
```

## Gaps
- list_elements max_depth=4 → 8052ms SLOW
- find_element Guardar → 11653ms SLOW
- Scope leak: Document id=15 del Notepad en árbol del diálogo

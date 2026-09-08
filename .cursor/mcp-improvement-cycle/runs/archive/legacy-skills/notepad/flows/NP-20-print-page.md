# NP-20 — Imprimir / Configurar página

## Pasos
```
invoke_element(Archivo) → Configurar página...
set_target_window("Configurar página")
list_elements  → mapa dialog
invoke_element(Aceptar)
invoke_element(Imprimir...)
set_target_window("Imprimir")
list_elements(role=Button)
send_keys("escape")  # no imprimir real
```

## Estado: pending

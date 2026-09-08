# Modal — Confirmar guardar

## Título: `Bloc de notas` (mismo que padre) · Clase `#32770`

## Disparadores
- Alt+F4 con texto sin guardar
- Nuevo con texto sin guardar
- Abrir otro archivo

## Botones (ES)
- Guardar
- No guardar
- Cancelar

## Secuencia
```
send_keys("alt+f4")
list_windows  → modal #32770
find_element(role=Button, name="No guardar")
invoke_element
list_windows  → ventana principal cerrada
```

## Estado: pending

# NP-06 — Cerrar sin guardar

## Pasos
```
set_element_value(automation_id="15", value="sin guardar test")
send_keys("alt+f4")
set_target_window("Bloc de notas")  # modal confirmación
invoke_element(name="No guardar", role="Button")
element_exists(window_title="Bloc de notas")  → false
list_windows  → Notepad cerrado o nuevo
```

## Estado: pending

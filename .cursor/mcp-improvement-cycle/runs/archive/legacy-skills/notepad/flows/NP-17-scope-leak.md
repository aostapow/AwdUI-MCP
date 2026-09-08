# NP-17 — Scope multi-ventana

## Objetivo
Verificar que get_all_values / list_elements no mezclan Calculadora + Notepad.

## Pasos
```
launch_app notepad + calculadora abiertas
set_target_window("Bloc de notas")
get_all_values  → solo editor id=15, NO Units1/Units2
list_elements  → solo nodos Notepad HWND
```

## Bug GAP-NP-001/005 — retest tras fix cache

## Estado: pending

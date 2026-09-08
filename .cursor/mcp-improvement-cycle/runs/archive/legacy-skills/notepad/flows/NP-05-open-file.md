# NP-05 — Abrir archivo

**Estado:** met · **2026-09-06**

## Menú (con foco)

1. `focus_window` "Bloc de notas"
2. `invoke_element` MenuItem Archivo — **283ms**
3. `list_elements` role=MenuItem depth=4 — **1724ms**
4. `invoke_element` Abrir id=2 — **816ms** ✓
5. `set_target_window` "Abrir"
6. `fill_form` id=1148 filename
7. `invoke_element` Button Abrir id=1 — **2258ms** ✓

## Nota

`ctrl+o` no abrió diálogo sin foco explícito en editor (focus_policy=minimal).

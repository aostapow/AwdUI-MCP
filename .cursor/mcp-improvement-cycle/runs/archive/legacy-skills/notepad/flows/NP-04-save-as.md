# NP-04 — Archivo → Guardar como

**Estado:** met · **2026-09-06**

## Atajo preferido

`send_keys` **ctrl+shift+s** → scope `Guardar como` → `fill_form` → `invoke_element` Guardar.

## OBS → ACT → VERIFY

| Paso | Tool | Timing | Resultado |
|------|------|--------|-----------|
| 1 | `send_keys` ctrl+shift+s | ~40ms | Diálogo #32770 |
| 2 | `set_target_window` "Guardar como" | ~38ms | Scope modal |
| 3 | `fill_form` id=1001 np04_test_mcp.txt | ~350ms | filled=1/1 |
| 4 | `invoke_element` Button Guardar id=1 | 1973ms (ok) | ✓ verified |
| 5 | `list_windows` | ~120ms | Título `np04_test_mcp.txt: Bloc de notas` |

## Modal

Ver [modals/save-as.md](../modals/save-as.md).

## Quirk

- `invoke_element` Archivo puede fallar sin `focus_window` previo; atajo de teclado más fiable.
- `find_element` Guardar en diálogo: SLOW ~11s — usar `invoke_element` con automation_id=1.

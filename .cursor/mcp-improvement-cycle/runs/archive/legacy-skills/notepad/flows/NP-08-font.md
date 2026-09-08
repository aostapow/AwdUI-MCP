# NP-08 — Fuente (ListBox + RadioButton)

**Estado:** met · **2026-09-06**

## OBS → ACT → VERIFY

| Paso | Tool | Timing | Resultado |
|------|------|--------|-----------|
| 1 | `invoke_element` Formato → Fuente... | ~800ms | Diálogo Fuente |
| 2 | `set_target_window` "Fuente" | ~38ms | Scope modal |
| 3 | `list_control_items` id=1000 | 6705ms ⚠ SLOW | Lista fuentes |
| 4 | `select_control_item` value=Consolas | ~350ms | OK SelectionItem |
| 5 | `invoke_element` Aceptar | ~400ms | Diálogo cierra |

## Retest MCP
`select_control_item` fallaba en nav Calculadora — **OK** en ListBox Win32 Fuente.

## Parámetro
Usar `value="Consolas"` (no `item_name`).

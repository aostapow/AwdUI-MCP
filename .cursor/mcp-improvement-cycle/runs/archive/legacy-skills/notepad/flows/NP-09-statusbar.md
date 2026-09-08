# NP-09 — Barra de estado toggle

**Estado:** met · **2026-09-06**

## Pasos

| # | Tool | Timing | Resultado |
|---|------|--------|-----------|
| 1 | `focus_window` Bloc de notas | ~85ms | Foco OK |
| 2 | `list_elements` role=StatusBar | 1611ms | id=1025 visible |
| 3 | `invoke_element` Ver | 271ms | Menú abierto |
| 4 | `find_element` "Barra de estado" id=27 | 185ms | MenuItem encontrado |
| 5 | `invoke_element` id=27 | 6348ms ⚠ | Toggle OFF — verify slow fail |
| 6 | `element_exists` id=1025 | ~55ms | NOT FOUND ✓ |
| 7 | `invoke_element` Ver + id=27 | 6558ms ⚠ | Toggle ON |
| 8 | `element_exists` id=1025 | ~55ms | OK exists ✓ |

## Quirk

- Item bajo **Ver** (no visible en `list_elements` depth=5; usar `find_element` name=Barra de estado).
- `invoke_element` verify post-menu ~6s y falla aunque la acción OK.

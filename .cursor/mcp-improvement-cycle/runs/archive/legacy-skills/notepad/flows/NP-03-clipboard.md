# NP-03 — Clipboard round-trip

**Estado:** met · **App:** Bloc de notas Win32 · **2026-09-06**

## OBS → ACT → VERIFY

| Paso | Tool | Timing | Resultado |
|------|------|--------|-----------|
| 1 | `type_text` "NP-03 clipboard test…" | ~300ms | 27 chars |
| 2 | `send_keys` ctrl+a | ~40ms | Selección |
| 3 | `send_keys` ctrl+c | ~40ms | Copia |
| 4 | `clipboard` action=read | ~50ms | Texto copiado OK |
| 5 | `clipboard` action=write "CLIPBOARD_WRITE_OK" | ~50ms | 18 chars |
| 6 | `send_keys` ctrl+a, ctrl+v | ~80ms | Pegado |
| 7 | `read_element` id=15 | ~400ms | value=CLIPBOARD_WRITE_OK ✓ |

## Notas

- Verificar con `read_element`/`spy_inspect`, no `get_all_values` solo (duplica Edit+Document).
- Requiere `focus_window` en Notepad antes de teclado si `focus_policy=minimal`.

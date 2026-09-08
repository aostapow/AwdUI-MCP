# Timings baseline — Notepad Win32 (DPI 1.25)

| Tool / flujo | ms | Verdict |
|--------------|-----|---------|
| `set_target_window` | 38 | fast |
| `invoke_element` Archivo (con foco) | 283 | fast |
| `invoke_element` submenu | 52–816 | ok |
| `list_elements` MenuItem depth=4 | 1724–4885 | slow ⚠ |
| `fill_form` dialog | 350 | ok |
| `invoke_element` dialog Button | 542–2258 | ok |
| `read_element` id=15 | ~400 | ok |
| `spy_inspect` id=15 | ~350 | ok |
| `select_control_item` Fuente | fast | ok |
| `list_control_items` fonts | 6705 | slow ⚠ |
| `scroll` pages=1 | fast | ok (0% diff doc corto) |
| `type_text` / `send_keys` | 40–300 | fast |

Meta agente: acción simple <500ms; investigar ≥3000ms.

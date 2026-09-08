# Gaps MCP — Notepad harness

| Gap | Severidad | Propuesta |
|-----|-----------|-----------|
| `list_elements` 2–8s | high | **Aplicado 2026-09-06:** fast path MenuItem cap≤6; sin comtypes depth-100 |
| `invoke_element` verify 10–17s en modales | high | Timeout verify separado; skip verify en MenuItem |
| Foco teclado no garantizado | medium | **Aplicado 2026-09-06:** `ensure_client_focus` en `send_keys`/`type_text` (Win32 + target) |
| `click_element` MenuItem Edición FAIL | medium | **Aplicado 2026-09-06:** `MenuItem_bbox_fallback` tras Invoke fail |
| Verify modal dismiss manual | high | **Aplicado 2026-09-06:** `verify_modal_dismissed` en click/invoke |
| Scope leak a Cursor si target mal | medium | `list_elements` debe filtrar por HWND target |
| `start_event_monitor` timeout COM | blocker | Fix event sidecar (ver state blockers) |
| Find/Replace Win11 sin modal #32770 | low | Skill: panel inline; OCR fallback |
| Modales stale reciben teclado | high | Recovery L1 obligatorio; ver protocol/recovery.md |
| `get_all_values` duplica Document+Edit | low | Dedupe por automation_id+role |

## Fix aplicado este ciclo

- `spy_props_to_element`: extrae `Value` pattern → `read_element` y `get_all_values` devuelven texto real.

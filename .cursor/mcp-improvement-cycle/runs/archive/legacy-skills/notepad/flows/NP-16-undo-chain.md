# NP-16 — Deshacer cadena

**Estado:** met · **2026-09-06**

## Pasos
```
type_text("UNDO_TEST")
read_element(automation_id="15")  → contiene UNDO_TEST
send_keys("ctrl+z")
read_element(automation_id="15")  → sin UNDO_TEST ✓
```

## Verify
Preferir `read_element` (Value via spy) sobre `get_all_values`.

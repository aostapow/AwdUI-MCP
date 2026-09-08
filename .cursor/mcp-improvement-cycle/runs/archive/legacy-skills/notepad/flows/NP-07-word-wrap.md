# NP-07 — Ajuste de línea (Word Wrap toggle)

**Estado:** met · **2026-09-06**

## Quirk Win11 ES
**Ajuste de línea** está bajo **Formato** (`automation_id=32`), no bajo Ver.

## Pasos
```
focus_window("Bloc de notas")
invoke_element(name="Formato", role="MenuItem")
invoke_element(name="Ajuste de línea", role="MenuItem", automation_id="32")
  → 7103ms SLOW (verify integrado)
ui_fingerprint  → layout cambió
```

## Patterns
MenuItem Toggle

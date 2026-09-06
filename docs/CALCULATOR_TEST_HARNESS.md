# Calculator Test Harness

Harness de pruebas vivas con **evidencia empírica** para validar cambios en AwdUI MCP.

## Ejecutar

```powershell
# Smoke rápido (2+2=4 con screenshot)
python scripts/smoke_calculator.py

# Integration pytest
$env:AWDUI_SKIP_VIRTUAL_DESKTOP = "1"
pytest tests/integration/test_calculator.py -q --tb=short
```

## Evidencia

- Screenshots: `tests/integration/evidence/`
- Log de corridas: `tests/integration/evidence/last_run.json`
- Fallos pytest: `tests/integration/failures/`

## Verificación de resultado

1. UIA (`read_display_uia`) — preferido
2. Screenshot + OCR (`find_text`) — si UIA no lee el display
3. Assert falla con ruta al PNG si no coincide

## Expresiones estándar

| Expresión | Esperado |
|-----------|----------|
| 2 + 2 | 4 |
| 15 * 7 | 105 |
| 12 + 8 | 20 |
| 100 / 4 | 25 |

## Recovery

Si hay timeout o modal inesperado, `tests/integration/recovery.py` captura screenshot, intenta ESC/OK/refocus (máx 3 intentos) y reintenta.

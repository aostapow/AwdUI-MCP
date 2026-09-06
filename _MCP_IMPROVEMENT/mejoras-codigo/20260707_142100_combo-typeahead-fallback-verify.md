# Combo WinForms sin items UIA: fallback type-ahead con verificación obligatoria

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-07-07 14:21:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | `mcp-servers/awdui-server/tools/control_items.py`, `detection/uia_find.py` |
| **Tool afectada** | `select_control_item`, `list_control_items` |
| **Tipo de gap** | tool_gap |
| **Nivel** | L4 |
| **Impacto** | alto |

## Resumen

**Problema:** En AST Time Report, `list_control_items` devuelve `returned=0` para `cboActividad`,
`cboGrupo` y `cboConcepto` aunque el combo responde a type-ahead (click + tipear + ↓ + Enter).
El agente reintentó 15+ veces con `set_element_value`, `select_control_item`, `alt+down`,
`list_control_items` y teclado manual. En `cboActividad`, type-ahead sin verificar seleccionó
actividad **38608** en lugar de **108082** — riesgo de datos incorrectos.

**Solución:** Cuando expand + `collect_control_items` devuelve 0 items en ComboBox WinForms:
1. Focalizar combo, `type_text(filter)` con delay corto.
2. `send_keys("down")` + `send_keys("enter")` (o listar popup post-type si aparece).
3. **Verificación obligatoria:** `Value` debe contener el substring pedido; si no → `success: false`
   con `actual_value` y sugerencia de lookup.
4. Exponer método en respuesta: `via typeahead` (análogo a `via set_value` prohibido).

**Dónde:** `_select_from_combo_popup` en `control_items.py`; opcional mejora de
`_popup_list_roots` en `uia_find.py` para capturar popup tras tipeo.

## Contexto del turno

- `list_control_items(cboActividad|Grupo|Concepto)` → 0 items (×6 llamadas).
- `select_control_item` → not found (×2).
- `set_element_value(cboActividad)` → solo código parcial, no actividad completa.
- Type-ahead manual en actividad → valor incorrecto 38608.
- Mismo patrón manual en grupo/concepto → OK pero ~12 tools cada uno.
- Lookup `btnBuscar` resolvió actividad en 4 tools adicionales.

## Cambio propuesto (pseudodiff)

```python
# control_items.py — tras fallo de popup list vacío:
def _select_combo_typeahead(raw, value: str) -> dict:
    focus_and_clear(raw)
    type_text(value)
    time.sleep(0.3)
    # intentar collect_control_items con include_popup=True de nuevo
    # si sigue vacío: send_keys down + enter
    current = _read_control_value(raw)
    if not _value_matches_selection(current, value):
        return {"success": False, "error": "...", "actual_value": current, "hint": "use lookup"}
    return {"success": True, "method": "typeahead", "verified_value": current}
```

## Verificación de duplicados

- `aceptadas/mejoras-codigo/20260707_024700_combo-select-verify-no-set-value.md` — cubre anti-`set_value`; no cubre type-ahead cuando no hay ListItem.
- `aceptadas/mejoras-tool/20260707_011000_list-combo-items.md` — consolidado en `list_control_items`; sigue sin resolver combos sin hijos UIA.

## Test de abstracción

- L4: aplica a WinForms ComboBox con autocompletado (DevExpress, Telerik, combos editables) sin depender del nombre AST.

## Beneficios futuros

- Reduce ~20 tools por fila de carga cuando el combo no expone items.
- Evita selección silenciosa incorrecta (38608 vs 108082).
- Un solo `select_control_item` atómico con verificación vs 6–12 intentos manuales.

## Criterio de aceptación

- [ ] `tests/test_control_items.py`: mock combo sin descendants → typeahead path con verify pass/fail.
- [ ] Respuesta incluye `method: typeahead` y `verified_value`.
- [ ] Documentado en `docs/MCP_TOOLS_REFERENCE.md` bajo `select_control_item`.
- [ ] Sin regresión en combos con popup ListItem visible.

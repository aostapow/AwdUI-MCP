# Grillas DevExpress: leer valores de celda UIA (no OCR)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_tool |
| **Estado** | aplicada |
| **Fecha** | 2026-07-07 02:05:00 |
| **Usuario sesión** | ariel.ostapow |
| **Tool afectada** | list_control_items, select_lookup_row, select_control_item |
| **Módulo** | detection/grid_rows.py, detection/uia_find.py, tools/control_items.py |
| **Tipo de gap** | tool_gap |
| **Nivel** | L4 |
| **Impacto** | alto |

## Resumen

**Problema:** En grillas DevExpress/WinForms lookup, los `DataItem` exponen `name` anónimo
(`titulo row 0`) pero el **valor de celda** está en UIA (`Value` / `LegacyIAccessible`).
`list_control_items` filtraba solo por `name` → 0 matches → el agente cayó a `find_text` OCR
(varios minutos) para un doble click.

**Solución:** Módulo `grid_rows.py` que agrupa celdas por fila, lee texto vía UIA, y permite
`select_lookup_row(value=..., column=...)` en una llamada programática (<2s).

**Señal para el advisor:** si `list_elements(role=DataItem)` muestra celdas `* row N` y luego
el agente usa `find_text`/`click_text` en la misma grilla → **proponer siempre** (L4 tool_gap),
no clasificar como `ejecucion`.

## Criterio de aceptación

- [ ] `select_lookup_row(gcGrillaActividades, value="108082")` sin OCR
- [ ] Test `tests/test_grid_rows.py`
- [ ] Advisor documenta anti-OCR cuando UIA tiene celdas con valores
- [ ] Reinicio MCP verificado

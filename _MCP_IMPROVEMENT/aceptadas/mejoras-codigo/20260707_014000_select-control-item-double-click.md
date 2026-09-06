# select_control_item: SelectionItem y doble click en lookup grids

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | aplicada |
| **Fecha** | 2026-07-07 01:40:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | tools/control_items.py, tools/ui_automation.py |
| **Tool afectada** | select_control_item |
| **Tipo de gap** | tool_gap |
| **Nivel** | L4 |
| **Impacto** | alto |

## Versiones MCP

| MCP | Versión | Nota |
|-----|---------|------|
| user-awdui | v0.2.1 | `list_control_items` / `select_control_item` ya en server.py |

## Resumen

**Problema:** `select_control_item` hace un solo `do_click` en el centro del item. Los diálogos
lookup WinForms suelen requerir **doble click** para confirmar y cerrar el modal, o soportan
`SelectionItemPattern` sin click. El agente recurrió a coordenadas manuales y seleccionó fila
equivocada.

**Solución:** Antes del click, intentar `SelectionItem.Select()` (reutilizar lógica de
`repo_action.py`). Agregar parámetro `double_click: bool = false`; si true, enviar doble click
en el centro del item coincidente. Respuesta incluye `method` usado (`SelectionItem`, `click`,
`double_click`).

**Dónde:** `do_select_control_item` en `control_items.py`; schema en `ui_automation.py`.

## Cambio propuesto (pseudodiff)

```python
# control_items.py — do_select_control_item
def do_select_control_item(..., double_click: bool = False) -> dict:
    ...
    for item in batch.get("items", []):
        ...
        # 1) SelectionItem pattern on matched raw node
        try:
            from pywinauto.uia_defines import get_elem_interface
            get_elem_interface(item_raw, "SelectionItem").Select()
            if double_click:
                do_double_click(x, y)  # new helper in input_tools
            return {"success": True, "method": "SelectionItem" + ("+double_click" if double_click else "")}
        except Exception:
            pass
        # 2) fallback click / double_click at item center
        if double_click:
            do_double_click(x, y)
            return {"success": True, "method": "double_click", ...}
        do_click(x, y)
        return {"success": True, "method": "click_item", ...}
```

- `input_tools.py`: `do_double_click(x, y)` vía `mouse` o dos clicks con delay mínimo
- Tool docstring: «Use `double_click=true` for WinForms lookup grids after btnBuscar filter»

## Contexto del turno

Tras filtrar actividad `108082` en diálogo Buscar, el agente no usó `select_control_item` en el grid
del modal; hizo doble click manual en coordenadas incorrectas y confirmó actividad `38608`.

## Test de abstracción

Cross-app: lookup modals con `DataItem`/`ListItem` en WinForms. No específico de AST.

## Verificación de duplicados

- Extiende `list_control_items` / `select_control_item` del mismo turno (código ya mergeado).
- `20260707_011000_list-combo-items.md`: **consolidar** — listing cubierto por `list_control_items`;
  este artefacto cubre **selección confirmatoria** (double click / SelectionItem).
- Distinto de `mdi-window-scope` y `observe-ui-depth-cap`.

## Criterio de aceptación

- [ ] Test pytest en `tests/test_control_items.py`: mock SelectionItem + double_click flag
- [ ] `select_control_item(double_click=true)` documentado en `docs/AGENT_GUIDE.md`
- [ ] Sin regresión en selección de ComboBox dropdown (single click default)
- [ ] Reinicio MCP verificado

## Beneficios futuros

Selección atómica y repetible en grids de búsqueda; evita coordenadas manuales y filas por índice.

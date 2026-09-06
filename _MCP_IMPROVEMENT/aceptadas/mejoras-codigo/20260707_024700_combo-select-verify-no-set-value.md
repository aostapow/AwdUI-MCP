---
estado: aplicada
tipo_propuesta: mejoras-codigo
tipo_gap: tool_gap
nivel_abstraccion: L4
fecha: 2026-07-07
turno_ref: ast-carga-108082-fallida
implementado: 2026-07-07
---

| Campo | Valor |
|-------|-------|
| **Estado** | aplicada |

# Combo dropdown: prohibir set_value falso positivo + verificar selección

## Problema

`select_control_item` en `cboGrupo` / `cboConcepto` devolvía `via set_value` sin abrir el dropdown.
WinForms no considera el campo completo → `btnGuardar` queda deshabilitado.

## Cambio implementado

- `control_items.py`: combos usan `_select_from_combo_popup` (expand + lista popup + descendants).
- Verificación post-click: `Value` debe contener el substring pedido (`verified_value`).
- Eliminado fallback `set_element_value` para `ComboBox`.
- Tests en `tests/test_control_items.py`.

## Módulo

`mcp-servers/awdui-server/tools/control_items.py`

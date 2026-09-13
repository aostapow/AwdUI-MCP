# AceListView — selección de fila en modal owned (ACL Explorer)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 21:18:30 |
| **Usuario sesión** | ariel.ostapow |
| **Tool afectada** | `select_control_item`, `click_element`, `list_control_items`, `find_item_by_property` |
| **Módulo** | `mcp-servers/awdui-server/tools/ui_automation.py`, `detection/` |
| **Tipo de gap** | tool_gap |
| **Nivel** | L4 |
| **Versión MCP** | v0.4.0 (check_version up to date) |

## Resumen

**Problema:** En el modal **Seguridad avanzada — permisos** (owned `#32770`), la lista `AceListView` expone filas UIA pero `click_element` sobre `ListItem`/`ListViewSubItem` falla (sin InvokePattern útil); `ButtonViewAce` queda **disabled** hasta seleccionar fila. El agente recurrió a **coordenadas**; `click_element_hwnd` además falló por NameError (`do_click_element_hwnd` no importado — ver propuesta hermana `20260910_202207`).

**Solución:** (1) Resolver scope al **HWND del modal owned** (`set_target_window` por título o handle del diálogo). (2) `list_control_items(automation_id="AceListView")` o `find_item_by_property` en el List padre. (3) `select_control_item` con SelectionItem / LegacyIAccessible en la fila visible (índice 0 o por nombre de principal). (4) Fallback HWND-scoped click solo si SelectionItem no aplica, usando helper importado correctamente.

**Dónde:** Pipeline List/ListItem en `select_control_item`; documentar patrón en `control-catalog.md` § List en modales Win32 owned.

## Análisis del gap

| Fricción | tipo_gap | Nivel | Propuesta |
|----------|----------|-------|-----------|
| Coords obligatorias para habilitar Ver | tool_gap | L4 | **Este archivo** |
| `click_element_hwnd` roto | tool_gap | L4 | `20260910_202207` — implementar primero |
| ListItem click sin selección | deteccion | L4 | Scope modal + SelectionItem |

## Contexto del turno

- Lab `escritorio-windows-2026-09-10`, execute **F-75** (`met` WARN).
- Evidencia: `evidence.jsonl` — click coords fila ACE; invoke `ButtonViewAce` 209 ms OK; `improvements.jsonl` friction AceListView.
- Tools: `set_target_window`, `invoke_element`, `read_element`, `click` (coords).

## Cambio propuesto (conceptual)

```python
# Tras resolver modal_hwnd como target o ancestor:
items = list_control_items(automation_id="AceListView", window_handle=modal_hwnd)
select_control_item(
    automation_id="AceListView",
    item_name=items[0]["name"],  # o index=
    window_handle=modal_hwnd,
)
# verify: get_control_state ButtonViewAce IsEnabled == True
```

Extender `select_control_item` para aceptar `window_handle` / `ancestor_automation_id` cuando el List no está bajo la ventana raíz del Explorer.

## Test de abstracción

Aplica a cualquier diálogo Win32 con `List` + botón acción condicionado a selección (permisos NTFS, listas ACE, pickers legacy) — no solo Explorer.

## Verificación duplicados

| Archivo existente | Acción |
|-------------------|--------|
| `20260910_202207_click-element-hwnd-missing-do-click-import` | **Dependencia** — habilitar fallback HWND |
| `20260906_175200_win32-modal-edit-hwnd-fallback` | Complemento modal owned |

## Criterios de aceptación

- [ ] F-75 re-ejecutable sin coords: `select_control_item` + `invoke_element` `ButtonViewAce`
- [ ] pytest: mock List con SelectionItem en modal scope
- [ ] `MCP_TOOLS_REFERENCE.md`: parámetro scope modal en `select_control_item` si se añade
- [ ] Tras fix `click_element_hwnd`, smoke con `window_handle` del modal

## Beneficios futuros

Flujos ACL / seguridad Explorer y modales Win32 similares dejan de depender de coords para habilitar botones downstream.

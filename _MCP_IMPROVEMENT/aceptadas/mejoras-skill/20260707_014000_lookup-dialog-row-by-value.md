# Lookup dialogs: seleccionar fila por valor, no por índice

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | aplicada |
| **Fecha** | 2026-07-07 01:40:00 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | awdui-flow-exploration |
| **Tipo de gap** | routing_tool |
| **Nivel** | L4 |
| **Impacto** | alto |

## Versiones MCP

| MCP | Versión | Nota |
|-----|---------|------|
| user-awdui | v0.2.1 | up to date |

## Resumen

**Problema:** Tras abrir un diálogo de búsqueda (lookup) WinForms, filtrar con `teFind` + `btFind`
y listar `DataItem` a nivel ventana, el agente asumió que la fila 0 era el resultado del filtro.
Seleccionó por doble click en coordenadas OCR o centro de bounds incorrectos, eligiendo una actividad
distinta a la buscada.

**Solución:** Documentar patrón «lookup dialog» en Fase 3/6: acotar scope al diálogo modal,
localizar el grid/list padre (`automation_id` o `role=DataGrid`/`List` dentro del diálogo),
usar `list_control_items` / `select_control_item` con `filter_text` o `value` igual al término
de búsqueda; nunca `list_elements(role=DataItem)` global ni asumir índice 0; validar con
`highlight_element` antes de confirmar.

**Dónde:** Fase 3 nueva subsección «Diálogos lookup»; Fase 6 tabla de acciones; anti-patrones.

## Texto propuesto

### Diálogos lookup WinForms (obligatorio)

Cuando un combo tiene botón `Abrir` / `btnBuscar` que abre modal de búsqueda:

1. `list_elements(window_title=<título del diálogo>, role="Button"|"Edit")` — mapear `teFind`, `btFind`, Aceptar
2. Tras filtrar: identificar contenedor del grid (`List`, `DataGrid`, `Table`) con `spy_inspect` o `list_elements` acotado al diálogo
3. `list_control_items(automation_id=<grid>, filter_text=<término buscado>)` — confirmar que aparece la fila esperada
4. `select_control_item(automation_id=<grid>, value=<término>)` con `double_click=true` si el flujo humano confirma con doble click
5. Si el diálogo no cierra con Enter: `invoke_element` en botón Aceptar/OK o `send_keys("{ESC}")` solo tras verificar título del diálogo
6. **Prohibido:** `list_elements(role=DataItem)` sin `window_title` del diálogo; click en fila 0; mezclar coordenadas OCR con bounds UIA de otro elemento

### Anti-patrones — agregar

- Asumir que `DataItem` índice 0 es el resultado de un filtro de búsqueda
- `click_text` / OCR en filas de grid cuando `list_control_items` devuelve el nombre esperado
- Doble click en coordenadas distintas al centro del `DataItem` listado sin `highlight_element`

## Contexto del turno

Retoma 2ª carga AST Time Report: búsqueda `108082` en diálogo Buscar OK, pero doble click seleccionó
`38608 - Tareas_Reuniones_Presidencia` (fila incorrecta). `list_elements(role=DataItem)` mostró
título de row 0 en (521,305); el click fue en (675,317). Grid inferior aún tenía fila de la 1ª carga.

## Test de abstracción

Cross-app: cualquier WinForms con lookup modal (combo + btnBuscar + grid). No depende de automation_ids
concretos del turno.

## Verificación de duplicados

- Complementa `20260707_011000_filtrar-combos-antes-ocr.md` (combos cerrados) — este cubre **grid en modal**.
- Tema manifiesto `ocr-before-uia` / `routing-tool`: **consolidar** ambas skill al aplicar.
- No duplica `20260707_011000_mdi-window-scope.md` (scope ventana hija del proceso principal).

## Criterio de aceptación

- [ ] Texto sin nombres de app ni automation_ids del turno
- [ ] Menciona `list_control_items` / `select_control_item` como vía primaria
- [ ] Anti-patrón «fila 0 tras filtro» explícito
- [ ] Coherente con Fase 5 (highlight antes de click)

## Beneficios futuros

Evita selección errónea en lookups repetibles; reduce OCR en grids cuando UIA expone `DataItem` con nombre.

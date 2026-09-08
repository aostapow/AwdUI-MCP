---
name: ast-activities-manager
description: >-
  Automatizar AST - Activities Manager (WinForms): navegación a módulos,
  Time Report, carga de horas y diálogos lookup. Usar cuando el usuario
  mencione AST, Activities Manager, Time Report o carga de horas.
---

# AST — Activities Manager

Skill **específica del producto**. Metodología: [metodologia-ui.md](../awdui-mcp-automejora/references/metodologia-ui.md). WinForms: [winforms.md](../awdui-mcp-automejora/references/patterns/winforms.md). Narración: [action-narration.md](../awdui-mcp-automejora/references/patterns/action-narration.md). **Repo:** tras mapear un control estable (`cboActividad`, `btnGuardar`, …) → `repo_capture` + `repo_hints_set` con quirks (ej. invoke falla → click). Antes de repetir → `repo_hints`. Ver [object-repository.md](../awdui-mcp-automejora/references/patterns/object-repository.md).

## Contexto de la app

| Campo | Valor |
|-------|-------|
| Ventana principal | `AST - Activities Manager` (parcial: `AST`) |
| Framework | WinForms |
| Backend | UIA |
| Target | `set_target_window("AST")` al inicio; `set_target_window("")` al terminar |

## Ventanas conocidas

| Ventana lógica | Título parcial | Notas |
|----------------|----------------|-------|
| Principal | `AST` | MDI host |
| Carga de horas | `Carga de Horas` | Formulario hijo; requiere target `AST` para scope |
| Buscar actividad | `Buscar` | Modal lookup; `id=wfBuscoActividad` |

## Mapa de objetos — Time Report / Carga de horas

Formulario **Carga de Horas** (ventana hija):

| Objeto lógico | automation_id | role | Interacción |
|---------------|---------------|------|-------------|
| Actividad (combo) | `cboActividad` | ComboBox | Lookup vía `btnBuscar` |
| Buscar actividad | `btnBuscar` | Button | `invoke_element` suele fallar → `click` en centro UIA |
| Horas | `cboHoras` | ComboBox | `set_element_value` ej. `"2 hs, 0 min"`, `"6 hs, 0 min"` |
| Grupo | `cboGrupo` | ComboBox | `select_control_item(value="homologacion")` |
| Concepto | `cboConcepto` | ComboBox | `select_control_item(value="calendario")` |
| Guardar | `btnGuardar` | Button | `invoke_element` |
| Grilla cargas | `gcGrillaActividades` | Table | Verificación post-guardado |

Diálogo **Buscar** (`window_title="Buscar"`):

| Objeto lógico | automation_id | role | Interacción |
|---------------|---------------|------|-------------|
| Texto búsqueda | `teFind` | Edit | `set_element_value` o click + `type_text` |
| Filtrar | `btFind` | Button | `invoke_element` |
| Grid resultados | `gcGrillaActividades` | Table | `select_lookup_row(value=<término>, double_click=true)` |

## Flujos documentados

- [Carga de horas en Time Report](flows/time-report-hours.md)

## Quirks conocidos (solo AST)

- `btnBuscar`: `invoke_element` falla con error COM → usar `find_element` + `click` en centro.
- `click_element` en `btnBuscar` puede rechazar click por coordenadas si el control es «identificable» → `click(x,y)` directo.
- `set_element_value` con `window_title="Buscar"` a veces devuelve «Window not found» aunque `find_element` sí resuelve → fallback click en `teFind` + `type_text`; preferir `window_title="AST"` (modal embebido).
- `select_control_item` en ComboBox **dropdown** no debe reportar `set_value` — si ocurre, la selección falló; usar `list_control_items` + reintentar.
- Antes de `btnGuardar`: `spy_inspect` → `is_enabled` debe ser True.
- Coordenadas: `highlight_element` antes de `click` en botones con invoke fallido (find vs highlight pueden diferir).
- Navegación inicial a Time Report: históricamente OCR en `TIMEREPORT`; preferir menú UIA si está mapeado.
- Tras lookup: **nunca** asumir fila 0; usar `select_lookup_row(gcGrillaActividades, value=<término>)` — **prohibido OCR** si UIA expone celdas `* row N`.

## Dónde registrar mejoras de esta app

Descubrimientos **solo de AST** (IDs, menús, flujos, quirks) → esta skill o `flows/`.

Mejoras **cross-app** (tools MCP, patrones WinForms genéricos, performance) → `awdui-mcp-automejora` o `_MCP_IMPROVEMENT/`.

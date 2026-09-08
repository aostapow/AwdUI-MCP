# Manifiesto AwdUI MCP Improvement Advisor

Referencia para el subagente `awdui-mcp-improvement-advisor`.

## Alcance

- Turnos con automatización Windows vía `user-awdui`.
- Default `estado: ninguno`; propuestas L3–L4 con `tipo_gap` válido.
- Backlog en `_MCP_IMPROVEMENT/`; mantenedores aplican cambios en repo.

## Mantenedores

| Usuario |
|---------|
| `ariel.ostapow` |

## Dueño del concern

| Concern | Dueño primario | Secundario |
|---------|----------------|------------|
| Metodología exploración → acción | `awdui-mcp-automejora/references/metodologia-ui.md` | `docs/AGENT_GUIDE.md` |
| **Role → leer / interactuar (catálogo)** | `patterns/control-catalog.md` (40 control types MS) | `patterns/control-patterns-reference.md` |
| Patrones WinForms cross-app | `awdui-mcp-automejora/references/patterns/winforms.md` | AGENT_GUIDE |
| Mapa de objetos / flujos de un producto | `{producto}/` ej. `ast-activities-manager` | — |
| Orden anti-OCR prematuro | `patterns/winforms.md` o skill producto | flow-exploration Fase 3 |
| `list_elements` profundidad, roles, offscreen | `list_elements` tool | `uia_backend.py` |
| Ventana hija / MDI no matchea `window_title` | `target_window.py`, `windows.py` | `list_windows` |
| ComboBox/ListBox sin items en árbol | `repo_action` Select | nueva `list_combo_items` |
| Combo editable + botón Abrir / lookup | `click_element`, `invoke_element` | `smart_find` |
| WinForms custom grid (DevExpress, etc.) | `detection/grid_rows.py`, `select_lookup_row` | `list_control_items` |
| OCR usado con celdas UIA visibles | **tool_gap L4** — `grid_rows`, leer Value/LegacyIAccessible | skill anti-OCR |
| Lentitud / timeouts | `observe_ui_tool`, `ui_fingerprint` | `perf.py`, fast mode defaults |
| OCR scope incorrecto | `find_text`, `click_text` | `ocr.py` |
| Focus terminal roba ventana | `set_target_window` | `awdui-mcp-automejora` Fase 0 |
| Object repository | `repo_find`, `repo_capture` | `repo_store.py` |
| Batch / secuencias | `batch_actions` | `input_tools.py` |

## Catálogo de tools (evaluar en fricciones)

| Tool | Uso esperado | Señal de mal uso |
|------|--------------|------------------|
| `set_target_window` | Inicio de sesión GUI | OCR full-screen, focus perdido |
| `detect_framework` | Fase 1 exploración | Saltada en WinForms estándar |
| `list_elements` | Mapeo con `max_depth` escalonado | Solo `max_depth=5` en formulario anidado |
| `list_elements(role=…)` | Filtrar ComboBox, Button, Edit | Barrido plano sin filtro |
| `spy_tree` / `spy_inspect` | Diagnóstico profundo | Reemplazo de list_elements en cada paso |
| `get_element_properties` | Confirmar patterns de un control | Antes de encontrar el control |
| `smart_find` | Cascada cuando localizador incierto | Primera opción con nombre parcial |
| `repo_action` Select/Set | ComboBox WinForms por valor | OCR para texto de combo |
| `invoke_element` | Botones con InvokePattern | `click_element` en combos |
| `set_element_value` | Edit con ValuePattern | Clicks + type_text en combo |
| `click_text` / `find_text` | Custom paint / sin UIA | **Prohibido** si UIA ya mostró celdas con valor (`* row N`) |
| `observe_ui_tool` | Snapshot inicial | En cada paso del flujo |
| `screenshot(capture=true)` | Verificación final | Tras cada click |
| `plan_probes_tool` | Menús/tabs ocultos | No usado cuando árbol vacío |
| `check_version` | Advisor + diagnóstico | — |

## Consulta de versión MCP

| Servidor | Herramienta |
|----------|-------------|
| `user-awdui` | `check_version`, `get_server_info` |

Registrar en propuestas: versión instalada, `updateAvailable` si existe.

## Temas con consolidación obligatoria

Si hay ≥2 propuestas abiertas del mismo tema → sugerir merge, no ADD.

| Tema (slug) | Acción |
|-------------|--------|
| `combo-items`, `list-combo`, `expand-combo` | Una spec de tool unificada |
| `child-window`, `mdi-window`, `window-scope` | Un cambio en resolución de ventana |
| `max-depth`, `list-elements-default` | Un cambio en defaults + doc |
| `ocr-before-uia`, `routing-tool` | Un bloque L4 en `patterns/winforms.md` o skill producto |
| `observe-slow`, `timeout`, `performance` | Un issue de performance con métricas |

## Batería de tests (artefactos)

| # | Test | Falla → |
|---|------|---------|
| 1 | **Cross-app:** ¿Otra app WinForms se beneficia? | `sintoma_app` |
| 2 | **Abstracción L3+** | No proponer |
| 3 | **Consolidación:** ¿Duplicado en backlog? | Sugerir merge |
| 4 | **Dueño correcto** | Reasignar |
| 5 | **Ya documentado:** ¿Está en SKILL o AGENT_GUIDE? | `ejecucion` o «mover al inicio» |
| 6 | **Código vs skill:** ¿El MCP puede ya y el agente no sabe? | Proponer skill, no código |
| 7 | **Tests:** ¿Hay test pytest para el cambio de código? | Incluir en criterio aceptación |

## Señales de mejora de código (L4)

Proponer cambio en `mcp-servers/awdui-server/` cuando:

- UIA expone el control con `automation_id` pero ninguna tool lista hijos/items.
- `window_title` no resuelve ventanas hijas del proceso target.
- `list_elements` default oculta controles estándar WinForms (>3 niveles de `Pane`).
- `repo_action` Select falla por falta de `ExpandCollapse` en combo cerrado.
- Herramientas de observación superan 30s sin necesidad de screenshot.

## Módulos de código frecuentes

| Módulo | Responsabilidad |
|--------|-----------------|
| `detection/backends/uia_backend.py` | Walk tree, expand, patterns |
| `tools/ui_automation.py` | list_elements, find, click |
| `tools/repo_action.py` | Select, Set, Swf* methods |
| `tools/target_window.py` | Focus y scope de ventana |
| `tools/ocr.py` | OCR scope y performance |
| `tools/framework_detect.py` | Hints por toolkit |
| `detection/winforms_map.py` | SwfComboBox, perfiles |

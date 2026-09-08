# Narración de acciones — observador en chat

> **Obligatorio** en todo turno con tools MCP sobre GUI Windows (`user-awdui`).
> El observador debe leer en el chat **qué se pretende hacer** antes de verlo en la aplicación.

Complementa OBS→ACT→VERIFY de [metodologia-ui.md](../metodologia-ui.md) y [evaluacion-lab.md](../evaluacion-lab.md).

## Qué es y qué no es

| Sí | No |
|----|-----|
| Anunciar intención para quien supervisa la pantalla | Pedir permiso al usuario («¿puedo clickear?») |
| Una frase clara + una tool + resultado | Ejecutar en silencio y resumir al final |
| Compatible con ciclo MCP automático (`sin pedir permiso` del hook) | Detenerse a esperar OK humano entre pasos |

**Narrar ≠ confirmar.** El agente actúa de inmediato tras el bloque «Voy a»; el observador solo anticipa qué verá.

## Regla dura

**Antes de invocar cada tool MCP que observe o modifique la UI**, escribir en el chat un bloque corto en español en el **mismo mensaje del agente**, encima de la tool (texto primero, tool después).

**Prohibido:**

- Un mensaje con varias tools GUI en paralelo sin texto entre ellas.
- Lanzar la tool en un mensaje que no contiene el bloque «Voy a» previo (salvo **retry** del mismo paso tras FAIL — re-narrar en una línea).

| # | Regla |
|---|--------|
| N1 | **Un turno = un bloque «Voy a» + una tool GUI + resultado** (no batch) |
| N2 | Lenguaje para humanos primero; `automation_id` / nombre de tool después |
| N3 | Indicar **ventana/contexto** si hay modales o varias instancias |
| N4 | Tras la tool: **Resultado** (OK / FAIL / DUDOSO) + evidencia breve |
| N5 | Si FAIL/DUDOSO: diagnosticar narrado antes del siguiente «Voy a» |

## Alcance — qué tools narrar

### Narrar siempre (OBS / ACT / VERIFY sobre la app)

Exploración y estado: `list_windows`, `list_desktop_windows`, `get_focused_element`, `list_elements`, `spy_tree`, `find_element`, `smart_find`, `get_snapshot`, `observe_ui_tool`, `ui_fingerprint`, `detect_framework`, `set_target_window`, `focus_window`, `restore_window`.

Acción: `click_element`, `invoke_element`, `double_click_element`, `set_element_value`, `type_into_element`, `type_text`, `send_keys`, `press_key`, `select_control_item`, `select_option`, `expand_element`, `scroll_element`, `fill_form`, `launch_app`, `attach_to_app`.

Verificación visible: `read_element`, `element_exists`, `wait_for_element`, `wait_for_change`, `screenshot`, `take_screenshot_optimized`, `screenshot_diff`, `find_text`, `click_text`.

### Exentas (meta MCP — sin bloque completo)

Solo una línea opcional si el turno es 100 % diagnóstico servidor:

`check_version`, `get_server_info`, `check_session_status`, `invalidate_cache`, `release_all`, `release_keyboard`, `check_java_bridge`, `detection_health`.

Si en el mismo turno mezclás meta + GUI → narrar **cada** tool GUI con la plantilla completa.

## Plantilla por paso

```markdown
### OBS | ACT | VERIFY — <nombre corto del paso>

**Voy a:** <qué hacés en la app, en castellano claro>

- Contexto: ventana «…» / flujo F-03 / menú Formato abierto
- Tool: `nombre_tool`(<parámetros esenciales>)
- Esperado: <qué debería verse o cambiar en pantalla>

→ [ejecutar UNA tool MCP en este mensaje]

**Resultado:** OK | FAIL | DUDOSO
**Evidencia:** <timing ms, título ventana, valor leído>
```

## Ejemplos (castellano)

### Exploración (OBS)

**Voy a:** listar los controles visibles de la ventana principal para armar el mapa UIA.

- Contexto: ventana «Bloc de notas»
- Tool: `list_elements`(max_depth=2)
- Esperado: árbol con menús, combos y botones nombrados.

### Selección combo (ACT)

**Voy a:** abrir el combo **Horas** y elegir «2 hs, 0 min».

- Contexto: formulario Carga de Horas, `cboHoras`
- Tool: `select_control_item`(automation_id=`cboHoras`, value=`2 hs, 0 min`)
- Esperado: el combo muestra 2 horas.

### Texto en campo (ACT)

**Voy a:** completar el campo **Actividad** con el número 120754.

- Contexto: diálogo Buscar
- Tool: `set_element_value`(automation_id=`teFind`, value=`120754`)
- Esperado: el edit muestra el número antes de filtrar.

### Clic en botón (ACT)

**Voy a:** pulsar **Guardar** para registrar la fila de horas.

- Tool: `invoke_element`(automation_id=`btnGuardar`)
- Esperado: fila nueva en la grilla o mensaje de confirmación.

### Verificación (VERIFY)

**Voy a:** leer el combo Horas para confirmar que quedó en 2 hs.

- Tool: `read_element`(automation_id=`cboHoras`)
- Esperado: value contiene «2».

### Retry tras FAIL

**Voy a:** reintentar pulsar **Guardar** (mismo paso; el invoke anterior no cambió la grilla).

- Tool: `click_element`(automation_id=`btnGuardar`)
- Esperado: fila visible en `gcGrillaActividades`.

## Fases metodología → etiqueta en chat

| Fase | Etiqueta | Tools típicas |
|------|----------|----------------|
| 0–5 | `OBS` | `list_windows`, `list_elements`, `spy_tree`, `smart_find`, `highlight_element` |
| 6 | `ACT` | `click_element`, `invoke_element`, `set_element_value`, `select_control_item`, `type_text`, `send_keys` |
| Cierre paso | `VERIFY` | `read_element`, `element_exists`, `wait_for_element`, `ui_fingerprint`, screenshot hito |

## Lab y evidencia

En corrida lab, alinear chat con `evidence.jsonl`:

| Chat | evidence.jsonl |
|------|----------------|
| Bloque **Voy a** | `phase`: obs / act |
| **Resultado/Evidencia** | `phase`: verify + `timing_ms` |
| Mencionar `flow_id` en execute | campo `flow_id` |

## Repo (memoria entre sesiones)

Si usás `repo_path` o `repo_action`:

1. **Antes:** `repo_hints` → mencionar en el bloque «Voy a» cualquier workaround o verify documentado.
2. **Después de fricción:** `repo_hints_set(..., append=true)` con la lección del turno.

Ver [object-repository.md](object-repository.md).

## Anti-patrones

- Ejecutar 3 tools y explicar después qué pasó.
- «Listo» sin decir qué control se tocó.
- Narrar solo al inicio del turno y callar durante 10 acciones.
- Solo jerga (`invoke F-03`) sin decir qué ve el usuario.
- Confundir narración con pedir autorización y frenar el ciclo MCP.

## Exclusión

Usuario escribe **sin narrar** / **skip narration** en el mensaje → omitir bloques formales; igual reportar resultado tras acciones críticas.

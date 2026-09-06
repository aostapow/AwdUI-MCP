---
name: calculator-mcp-harness
description: >-
  App de prueba obligatoria: Windows Calculator (UWP). Hasta que esté cubierta
  de punta a punta solo con tools MCP (agentico), no pasar a otra app. Cero
  scripts Python/batch para evaluar o cubrir la UI. Evidencia empírica con
  OBSERVAR→ACTUAR→VERIFICAR y screenshots en cada hito.
---

# Calculadora UWP — laboratorio MCP (app parámetro)

## Mandato (leer antes de cada turno con Calculadora)

1. **La Calculadora es la única app de prueba** hasta que `calculator_perfect` sea `true` en `state.json`.
2. **No es el producto** — valida tipos de objeto y patterns que mañana aplicarán a otras apps Windows.
3. **Evaluar solo de forma agentica** — tools MCP, un paso por vez, leyendo el resultado en el chat.
4. **Cobertura = descubrimiento completo por pantalla**, no “prueba mínima” (un botón y cerrar).
5. **Los scripts Python no validan cobertura** — prohibidos para decidir `calculator_perfect` / `objective_met`.

Lo único permitido fuera del agente: **pytest unitario** del código en `mcp-servers/awdui-server/` (no prueba la app entera).

---

## Qué NO significa “el MCP funciona”

| Afirmación falsa | Por qué es falsa |
|-----------------|------------------|
| “`objective_met` infra = Calculadora perfecta” | Infra solo prueba un **corte** (ej. modo Estándar, un botón, un ciclo). |
| “`list_elements` devolvió 30 botones” | No implica los 9 modos, menús, flyouts ni historial. |
| “`invoke_element` OK una vez” | No implica todos los controles ni rapidez en todos los modos. |
| “Corrimos un script y pasó” | **No cuenta** como evidencia de cobertura ni de evaluación. |
| “`spy_tree` listó nodos” | No sustituye **actuar + verificar** cada función relevante. |

**Solo cuenta** lo que el agente hizo **en vivo** con MCP y documentó en `state.json` + evidencia citada en el turno.

---

## Qué SÍ significa “Calculadora perfecta” (`calculator_perfect: true`)

Todas las condiciones siguientes, con **evidencia agentica** (ver sección Evidencia):

### A. Navegación y modos (9 modos NavView)

Abrir nav (`TogglePaneButton` → `invoke_element`), para **cada** `automation_id`:

| automation_id | Modo (locale ES) |
|---------------|------------------|
| `Standard` | Estándar |
| `Scientific` | Científica |
| `Graphing` | Graficar |
| `Programmer` | Programador |
| `Date` | Fecha |
| `Currency` | Divisa |
| `Volume` | Volumen |
| `Length` | Longitud |
| `SettingsItem` | Configuración |

**Por cada modo:**

1. **OBSERVAR:** `invoke_element` con `SelectionItemPattern` (ListItem) o pattern documentado.
2. **VERIFICAR:** `spy_inspect` `Header` → texto contiene el modo esperado.
3. **OBSERVAR:** `list_elements` `role=Button` → contar botones con `automation_id`; guardar número en evidencia.
4. **SCREENSHOT:** `screenshot` `scope=window` tras estabilizar UI; anotar ruta en evidencia.

**Criterio modo OK:** Header correcto + árbol con botones/controles esperados (no 0, no solo shell MSAA) + screenshot.

### B. Chrome y paneles (toda la app)

| Control | automation_id / señal | Acción agentica | Verificación obligatoria |
|---------|----------------------|-----------------|---------------------------|
| Nav | `TogglePaneButton` | `invoke_element` abrir/cerrar | Botón cambia name o nav visible en `spy_tree` |
| Historial | `HistoryButton` o control equivalente en chrome | `invoke_element` | Panel/flyout visible en `list_elements` / `spy_tree` + screenshot |
| Memoria | `MemoryButton`, `memButton`, `MemPlus`, `MemRecall`, `ClearMemoryButton`, `MemMinus` | invoke cada control aplicable | Display o panel memoria cambia (`CalculatorResults` / texto UIA) |
| Always on top | `NormalAlwaysOnTopButton` | `invoke_element` | Estado toggle en `spy_inspect` si expone pattern |
| Configuración | `SettingsItem` | `SelectionItem` | Pantalla settings: `list_elements` no vacío + screenshot |

### C. Descubrimiento completo por pantalla (reemplaza “mínimo”)

**No alcanza** con abrir un modo o pulsar un botón. Por cada pantalla estable:

```
screenshot → list_elements + spy_tree → tabla de objetos
→ por cada objeto: ¿patterns? ¿acciones posibles? → actuar → verificar cambio
```

| Tipo de pantalla | Qué demostrar |
|------------------|---------------|
| **Estándar** | Todos los botones del teclado + memoria + historial/flyouts; expresión aritmética completa con display UIA |
| **Científica** | Cada función visible (trig, log, potencias, constantes…) con invoke + verify display |
| **Programador** | Bases HEX/DEC/OCT/BIN, QWORD/DWORD, operadores bit visibles |
| **Graficar** | GraphingControl, zoom, settings, entrada de ecuación si existe |
| **Fecha / conversores** | Combos, campos fecha, unidades — interactuar y leer UIA |
| **Configuración** | Expanders, temas, about — listar y abrir cada sección |

**Pregunta por objeto:** “¿Qué podría hacer con este control?” — Invoke, SelectionItem, Value, ExpandCollapse, Toggle, Scroll…

Si un paso falla → **gap MCP** (fix en servidor), no workaround en script.

### C2. Mejora de skill cada turno

Si este turno tocó Calculadora, antes de cerrar:

- ¿Algo nuevo sobre NavView, flyouts, title bar, contaminación `list_elements`?
- ¿Atajo útil (ej. `Alt+1` → Estándar) o anti-patrón?
- → Actualizar **esta skill** o `awdui-flow-exploration/patterns/` con 3–10 líneas concretas.

### D. Calidad del MCP (no solo “funciona una vez”)

| Dimensión | Cómo evaluarlo (agentico) |
|-----------|---------------------------|
| **Programático** | Método en respuesta = `InvokePattern` / `SelectionItemPattern` / `Value` — no “click por coordenadas” salvo último recurso **documentado** en evidencia |
| **Rápido** | Anotar en evidencia si un `list_elements`/`spy_tree` tardó >15s o hubo timeout — es gap de performance |
| **Sin contaminación** | `list_elements` no debe mezclar botones de Cursor/Chrome; solo nodos XAML de Calculadora |
| **Repetible** | Mismo flujo OBS→ACT→VERIFY en un **segundo** turno sin “arreglos manuales” del usuario |

---

## Protocolo agentico por paso (obligatorio)

```
set_target_window("Calculadora")
get_target_window                    → citar resultado
list_windows                         → CalculatorApp.exe presente
[opcional] detect_framework            → uwp/winui

OBSERVAR:
  find_element / spy_inspect / list_elements / spy_tree
  → citar automation_id, role, count

ACTUAR (un solo control):
  invoke_element | set_element_value | …
  → citar success + method

VERIFICAR (al menos una):
  spy_inspect CalculatorResults | Header
  screenshot scope=window
  list_elements diff lógico (antes/después descrito en prosa)

REGISTRAR en state.json (criteria_status / calculator_matrix)
```

**Prohibido:** encadenar 20 acciones sin leer respuestas intermedias. **Prohibido:** background scripts.

---

## Evidencia empírica (sin scripts)

### Qué guardar cada turno

En `.cursor/mcp-improvement-cycle/state.json`:

- `calculator_matrix`: objeto por modo/fila con `status`: `not_started` | `partial` | `met`
- `calculator_evidence[]`: entradas `{ "ts", "phase", "observe", "act", "verify", "screenshot" }`
- `last_cycle.live_verify`: resumen **honesto** — qué se probó y qué **no**

### Screenshots (obligatorios en hitos)

| Hito | Cuándo |
|------|--------|
| Primer árbol OK de un modo | Tras `list_elements` ≥ umbral de botones |
| Tras operación aritmética | Display debe coincidir con lo leído en UIA |
| Flyout (historial, memoria) | Panel abierto |
| Fallo / blocker | Estado visible para diagnóstico |

Tool: `screenshot` con `scope=window`, `window_title=Calculadora`. Opcional: `screenshot_baseline` / `screenshot_diff` si hay regresión.

**Sin screenshot en el hito → el hito no está `met`.** Leer UIA del display no reemplaza screenshot en hitos de modo/panel; ambos en operaciones críticas.

### Inventario “todas las funciones”

No se afirma “descubrimos todo” sin:

1. `spy_tree` `max_depth` ≥ 12 en **cada modo** (citado en chat: count total).
2. Tabla en `calculator_matrix` con **cada** `automation_id` de botón listado al menos una vez.
3. Gaps explícitos: controles visibles en screenshot pero ausentes en UIA → `blockers` + tarea MCP.

---

## Matriz de cobertura (fuente de verdad en state.json)

El agente mantiene `calculator_matrix` en `state.json` (no en scripts). Plantilla:

```json
"calculator_matrix": {
  "nav_modes": {
    "Standard": { "status": "met", "buttons_with_aid": 30, "screenshot": "..." },
    "Scientific": { "status": "not_started" }
  },
  "panels": {
    "HistoryButton": { "status": "partial" }
  },
  "standard_arithmetic": { "status": "partial", "last_expr": "2+2=4" }
}
```

`calculator_perfect: true` solo si **todas** las filas requeridas (sección A+B+C) están `met` con evidencia.

---

## Checkpoint antes de decir “listo”

Responder en el turno (honesto):

| # | Pregunta |
|---|----------|
| 1 | ¿Probé **los 9 modos** con Header verificado? |
| 2 | ¿**Actué y verifiqué display** en Estándar (no solo `num1`)? |
| 3 | ¿Historial y memoria abiertos y verificados? |
| 4 | ¿Hay **screenshot** por cada modo al menos una vez? |
| 5 | ¿`list_elements` limpio (solo Calculadora)? |
| 6 | ¿Algún paso lo hizo un **script**? → entonces **no cuenta** |
| 7 | ¿`calculator_perfect` en state.json refleja la realidad? |

Una sola respuesta NO → `calculator_perfect` sigue `false`; `objective_met` sigue `false`.

---

## Gaps MCP típicos (arreglar en código, no en scripts)

1. UWP: `window_rect` ApplicationFrameHost vs CoreWindow (numpad fuera de bbox).
2. Nav ListItem: `SelectionItemPattern`, no `Invoke`.
3. FlaUI sidecar árbol débil → orchestrator debe caer a `uia` + spy.
4. Filtro XAML para no mezclar ventanas.
5. Flyouts/modales: scope de ventana activa antes de seguir en padre.

---

## Anti-patrones (explícitos)

- `python scripts/explore_calculator*.py` para “cubrir” la app
- `run_calculator_coverage.py` como gate de cierre
- `pytest tests/integration/test_calculator*.py` como prueba de que la app está OK
- Declarar “MCP perfecto” o “app de punta a punta” sin matriz + screenshots
- Pasar a AST u otra app con `calculator_perfect: false`
- `success: true` sin VERIFICAR display/árbol/screenshot

---

## Tests permitidos (solo código MCP)

```powershell
& "$env:USERPROFILE\.awdui-mcp\.venv\Scripts\python.exe" -m pytest tests/test_params_and_windows.py tests/test_window_visual_rect.py -q
```

Prueba de la **aplicación**: solo tools MCP en el agente.

---

## Referencias

- Objetivo global: [awdui-mcp-objective/SKILL.md](../awdui-mcp-objective/SKILL.md)
- Estado: `.cursor/mcp-improvement-cycle/state.json`
- Tools: `docs/MCP_TOOLS_REFERENCE.md`
- Seguridad GUI: `.cursor/rules/awdui-gui-safety.mdc`

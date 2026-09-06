---
name: awdui-mcp-objective
description: >-
  Objetivo durable del repo AwdUI MCP: automatización Windows programática y
  agentica. App de prueba: Calculadora UWP hasta calculator_perfect. Evaluación
  solo agentica (MCP tools); scripts Python no validan cobertura. No parar hasta
  objective_met y calculator_perfect en state.json.
disable-model-invocation: false
---

# Objetivo AwdUI MCP — agente de mejora continua

## Objetivo (no negociable)

**Construir un MCP que automatice aplicaciones Windows de forma programática, segura y agentica.**

| Sí | No |
|----|-----|
| Mejoras en `mcp-servers/awdui-server/` + tests **unitarios** del servidor | Scripts batch / `explore_calculator*` / gates Python para evaluar apps |
| Un paso MCP por turno con observación | Clicks a ciegas / coordenadas desatendidas |
| Verificar efecto (UIA + screenshot en hitos) antes del siguiente paso | Afirmar “probado de punta a punta” sin evidencia agentica |
| Calculadora **completa** antes de otra app | Saltar a AST con `calculator_perfect: false` |

**App de prueba actual (única):** Windows Calculator (UWP).  
**Siguiente app:** solo cuando `calculator_perfect: true` en `state.json`.  
Detalle de cobertura Calculadora: [calculator-mcp-harness/SKILL.md](../calculator-mcp-harness/SKILL.md).

---

## Dos niveles de “cumplido” (no confundir)

### Nivel 1 — Infraestructura MCP (`mcp_infra_ready`)

Capacidad técnica mínima del servidor (ej. árbol UIA visible, invoke en un botón, SelectionItem en nav).  
**No implica** que la Calculadora esté probada entera ni que el MCP sea “perfecto”.

### Nivel 2 — App de prueba perfecta (`calculator_perfect`)

Calculadora UWP cubierta según matriz en [calculator-mcp-harness/SKILL.md](../calculator-mcp-harness/SKILL.md): 9 modos, paneles, operaciones, screenshots, inventario UIA.

### Flag global `objective_met`

En `state.json`:

```text
objective_met = true  SOLO SI:
  mcp_infra_ready == true
  Y calculator_perfect == true
```

Si solo se cumplió infra → **`objective_met` debe ser `false`**. No hay excepciones.

---

## Fuente de verdad

Leer **al inicio de cada turno** y **antes de cerrar**:

```
.cursor/mcp-improvement-cycle/state.json
.cursor/skills/calculator-mcp-harness/SKILL.md   (si trabajás en Calculadora)
```

| Campo | Uso |
|-------|-----|
| `goal` | Objetivo en una frase |
| `completion_criteria` | Criterios de fin **globales** |
| `objective_met` | `true` solo si infra + Calculadora perfecta |
| `calculator_perfect` | `true` solo con matriz completa y evidencia agentica |
| `calculator_matrix` | Estado por modo/panel/operación |
| `calculator_evidence` | Log agentico (observe/act/verify/screenshot) |
| `current_focus` | Una tarea para este turno |
| `blockers` | Impedimentos reales, no ocultos |

**El chat no es memoria.** Actualizar `state.json` al cerrar cada turno con honestidad.

---

## Evaluación: solo agentico

### Qué cuenta como evidencia

| Cuenta | No cuenta |
|--------|-----------|
| Llamada MCP en el turno + resultado citado | “Debería funcionar” |
| `spy_inspect` / `list_elements` / `invoke_element` en vivo | Script Python que recorre la UI |
| `screenshot` en hitos (modo, panel, operación) | Solo pytest integration sin agente |
| Entrada en `calculator_evidence` | `mode_map.json` generado por script sin revisión agentica |
| pytest **unitario** del módulo MCP tocado | pytest integration como sustituto de cobertura GUI |

### Quién decide si se cumplió un criterio

**El agente**, en el turno, aplicando el checkpoint de [calculator-mcp-harness/SKILL.md](../calculator-mcp-harness/SKILL.md) y actualizando `criteria_status` / `calculator_matrix` con status `met` **solo** si hubo OBS→ACT→VERIFY (+ screenshot donde exige la skill).

Los hooks (`check_mcp_objective.py`) solo leen `objective_met` en JSON — **no** reemplazan la evaluación honesta del agente.

---

## Qué es “ver el árbol UIA”

UI Automation expone la UI como **árbol de nodos** (ventana → contenedores → controles):

- `automation_id` (preferido), `role`, `name`
- `patterns`: `Invoke`, `SelectionItem`, `Value`, etc.

**Observar** = `list_elements`, `find_element`, `spy_tree` devuelven nodos reales (no shell MSAA vacío).  
**Sin árbol → no actuar** (arreglar MCP, no coordenadas a ciegas).

---

## Ciclo agentico (una iteración por turno)

```
LEER state.json + calculator-mcp-harness SKILL
  → set_target_window("Calculadora")
  → OBSERVAR (list/find/spy_tree)
  → ¿árbol OK? Si no → fix MCP (un fix por ciclo)
  → ACTUAR (un control: invoke/selection/value)
  → VERIFICAR (CalculatorResults/Header + screenshot en hitos)
  → pytest unitario del módulo MCP tocado
  → ACTUALIZAR calculator_matrix, calculator_evidence, state.json
  → ¿calculator_perfect? ¿objective_met? Si no → continuar sin pedir permiso
```

---

## Criterios de fin (`completion_criteria` en state.json)

Deben incluir (como mínimo):

1. **Infra:** árbol UIA real, invoke/selection sin coords en controles XAML representativos.
2. **Calculadora — 9 modos:** cada modo con Header verificado + screenshot + conteo de controles.
3. **Calculadora — paneles:** historial, memoria, configuración verificados agenticamente.
4. **Calculadora — Estándar:** expresión aritmética completa con display verificado (UIA).
5. **Calculadora — por pantalla:** descubrimiento **completo** de objetos interactuables y sus patterns (ver skill Calculadora).
6. **Ciclo OBS→ACT→VERIFY** repetible solo con tools MCP (sin scripts batch).
7. **Evidencia:** `calculator_evidence` + inventario por objeto con screenshots en hitos.
8. **Tests unitarios** del servidor MCP por cada mejora de código.
9. **Skills:** al menos una mejora documentada por turno con fricción (skill genérica, harness o flow-exploration).

No marcar `met` en un criterio sin evidencia agentica de **ese** criterio.

---

## Reglas de persistencia

1. **No parar** mientras `objective_met` sea `false` **y el ciclo no esté pausado** (hook `stop` reinyecta).
2. **Stop manual del usuario:** si el usuario pulsa Stop en Cursor o pide parar → ejecutar `scripts/pause-mcp-cycle.ps1` **en ese turno** y **no** relanzar subagentes ni continuar el ciclo. Cerrar Cursor no debería ser necesario.
3. **Pausa explícita:** `scripts/pause-mcp-cycle.ps1` — hooks dejan de inyectar followup.
4. **No declarar Calculadora lista** con solo un modo o un botón.
5. **No scripts GUI** — `.cursor/rules/awdui-gui-safety.mdc`.
6. **Un fix MCP por ciclo** en el servidor (prioridad sobre acumular evidencia).
7. **No otra app de prueba** hasta `calculator_perfect: true`.
8. Subagentes en background **solo si** `cycle_control.paused` es false.

---

## Transparencia en chat (obligatorio)

Anunciar cada paso antes o al ejecutarlo, en una línea:

`[MCP] OBSERVAR invoke_element HistoryButton…` → `[MCP] resultado: InvokePattern 42ms`

El usuario debe ver **qué hacés** y **cuánto tarda** cada interacción. Si una acción simple (un botón) requiere >5 tools o >3s, es **gap MCP** → fix en servidor, no más workarounds.

---

## Prioridad del turno (orden)

1. **Objetivo skill:** MCP programático confiable (tipos de objeto, patterns, velocidad).
2. **Fix código** en `mcp-servers/awdui-server/` + test unitario si hubo fricción medida.
3. **Un ciclo OBS→ACT→VERIFY** en laboratorio (Calculadora hoy) con tiempos citados.
4. **Actualizar skill/pattern** si se aprendió algo reutilizable.
5. **state.json** — honesto, sin obsesión con marcar `met` sin fix.

**Anti-patrón:** 10+ llamadas MCP solo para “encontrar” un control que debería resolverse con `invoke_element` tras un fix.

---

## Medición de latencia (obligatoria)

Cada interacción debe medirse **de punta a punta** dentro de la tool MCP:

| Fase | Qué mide | Tools |
|------|----------|-------|
| **find** | Localizar el control | `find_element`, `list_elements` |
| **act** | Invoke / click / expand | `invoke_element`, `click_element`, `expand_element` |
| **verify** | Confirmar efecto en UI | `verify_automation_id` / `verify_name_contains` en invoke/click |

**Respuesta MCP** incluye desglose, ej.:
`Invoked via InvokePattern (total 412ms: find 180ms, act 95ms, verify 137ms) ✓ verified`

**Metas:**
- **< 500ms** total → `fast` (objetivo para botón XAML)
- **500–3000ms** → `ok`
- **≥ 3000ms** → `slow` ⚠ — investigar y mejorar MCP antes de seguir

**Protocolo agente:**
1. Preferir **una** tool con verify (`invoke_element` + `verify_automation_id`) en lugar de find + invoke + spy_inspect separados.
2. **Citar siempre** el timing de la respuesta en el chat.
3. Si `slow`: documentar en `blockers` / `_MCP_IMPROVEMENT` y priorizar fix de código.
4. Registrar en `state.json` → `last_cycle.timings[]` si hubo latencia anormal.

---

## Laboratorio vs objetivo real

**La app de prueba (hoy Calculadora) es solo un parámetro** — un medio para validar el MCP. Mañana puede ser AST u otra app WinUI/WinForms.

| Centro del desarrollo | No es el centro |
|----------------------|-----------------|
| Tipos de objeto UIA (Button, ListItem, ComboBox, Grid, Flyout…) | IDs concretos de Calculadora hardcodeados en código genérico |
| Patterns soportados por rol (Invoke, SelectionItem, Value, Expand…) | “Pasar la calculadora” como único éxito |
| Descubrir **todo** lo interactuable en cada pantalla | “Prueba mínima” (un click y listo) |
| Skills reutilizables por producto | Lógica de negocio de una app en el servidor MCP |

---

## Descubrimiento completo por pantalla (no “mínimo”)

Por cada **pantalla estable** (modo, panel, flyout, settings):

1. **Screenshot** `scope=window` — inventario visual.
2. **OBSERVAR** `list_elements` + `spy_tree` (profundidad suficiente) — inventario programático.
3. **Por cada objeto interactuable** (botón, combo, fila, toggle, hyperlink):
   - ¿Qué **patterns** expone? (`spy_inspect` / `discover_control_interaction`)
   - ¿Qué **acciones** son posibles además de click? (invoke, select, set value, expand, scroll…)
   - ¿Qué **cambia** en UI/display tras actuar? (VERIFICAR)
4. Registrar en `calculator_matrix` / `object_inventory` con status por `automation_id` o señal estable.
5. Gap: visible en screenshot pero ausente en UIA → `blockers` + fix MCP.

**Pregunta obligatoria por objeto:** “¿Qué podría hacer con este objeto?” — no solo “¿puedo hacer click?”.

---

## Mejora de skills cada turno (objetivo del ciclo)

Antes de cerrar el turno, evaluar:

| Pregunta | Acción si NO |
|----------|----------------|
| ¿La skill guió bien OBS→ACT→VERIFY? | Editar skill genérica o harness con patrón nuevo |
| ¿Hubo fricción repetida? | Añadir sección “quirk” o checklist en skill |
| ¿`list_elements` contaminado o lento? | Documentar workaround + propuesta MCP |
| ¿Faltó protocolo de pausa/stop? | Actualizar skill objetivo |

Las skills son **código operativo** del agente — mejorarlas es tan válido como fix en `awdui-server`.

| Pregunta | Si NO → |
|----------|---------|
| ¿`calculator_perfect` refleja la matriz real? | Mantener `false` |
| ¿`objective_met` solo si ambos niveles OK? | No poner `true` |
| ¿Evidencia **agentica** este turno (no script)? | No marcar `met` |
| ¿Screenshot en hitos que lo exigen? | Hito = `partial` máximo |
| ¿Inventario UIA por modo documentado? | No afirmar “todas las funciones” |
| ¿Fix implementado + pytest unitario? | No cerrar código |
| ¿Contaminación Cursor en `list_elements`? | Blocker activo |

---

## Respuestas honestas a preguntas del usuario

| Pregunta | Respuesta correcta del agente |
|----------|------------------------------|
| ¿MCP funciona perfecto? | Solo si `calculator_perfect` y evidencia lo respaldan; si no, **no**. |
| ¿App probada de punta a punta? | Solo si matriz A+B+C de calculator-mcp-harness está `met`. |
| ¿Hay evidencia? | Citar turnos MCP + rutas screenshot + `calculator_evidence`. |
| ¿Descubrimos todas las funciones? | Solo si `spy_tree` por modo + matriz de automation_ids completa. |
| ¿Chequeo visual? | Screenshots obligatorios en hitos; UIA sola no alcanza para “modo OK”. |

---

## Comandos útiles (solo estado y tests unitarios)

```powershell
python .cursor/hooks/check_mcp_objective.py --mode status
& "$env:USERPROFILE\.awdui-mcp\.venv\Scripts\python.exe" -m pytest tests/test_params_and_windows.py tests/test_window_visual_rect.py -q
```

---

## Anti-patrones

- Scripts `explore_calculator*`, `run_calculator_coverage`, orchestrator para evaluar
- `objective_met: true` con Calculadora a medias
- Integration pytest como prueba de la app
- Resumir y cerrar sin OBS→ACT→VERIFY
- Preguntar “¿sigo?” si `objective_met` es false

---

## Referencias

- Calculadora (detalle): [calculator-mcp-harness/SKILL.md](../calculator-mcp-harness/SKILL.md)
- Ciclo: [mcp-improvement-cycle/SKILL.md](../mcp-improvement-cycle/SKILL.md)
- Metodología UI: [awdui-flow-exploration/SKILL.md](../awdui-flow-exploration/SKILL.md)
- Misión: `.cursor/rules/awdui-mission.mdc`

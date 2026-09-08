# Metodología UI — exploración de flujos (AwdUI)

Parte de [awdui-mcp-automejora](../SKILL.md). Antes de ejecutar un flujo, **mapear objetos de forma programática**.
No clicar por coordenadas ni adivinar hasta tener un mapa estable ventana → padres → hijos.

## Reglas

0. **Ventana activa primero** — antes de actuar, evaluar qué ventana tiene el foco y qué se espera de ella. Si abrís un diálogo, completá el sub-flujo **en esa ventana** y verificá que **cerró** antes de volver al padre. Ver [patterns/active-window.md](patterns/active-window.md).
1. **Explorar antes de actuar** — ningún `click`, `click_element` o `type_text` hasta completar el mapa del paso actual.
2. **Top-down estricto** — ventana → contenedores padre → controles hijo.
3. **Target vs foco** — `set_target_window` define alcance UIA; el foco del SO define dónde llegan clic/teclado. No asumir que son lo mismo.
4. **Preferir identificadores estables** — en este orden: `automation_id` > `name`+`role` > `class_name` > OCR > coordenadas.
5. **Verificar antes de usar** — `highlight_element` o `smart_find` con `highlight=true` para confirmar el objeto correcto.
6. **Una tool a la vez** en Windows — no paralelizar llamadas AwdUI (COM/UIA).
7. **Bloqueado → entender, no reintentar** — si una acción no produce el efecto esperado, `list_windows` + screenshot para diagnosticar **qué ventana está activa** y qué falta cerrar o completar; no repetir el mismo click en el padre.
8. **Narrar antes de actuar** — cada tool MCP GUI requiere un bloque en chat («Voy a: …») **antes** de ejecutarla. Ver [patterns/action-narration.md](patterns/action-narration.md).
9. **Depositar aprendizaje en repo** — control estable o workaround → `repo_capture` / `repo_hints_set`. Ver [patterns/object-repository.md](patterns/object-repository.md).
10. **Lab / harness** — verify empírica + `evidence.jsonl`; ver [evaluacion-lab.md](evaluacion-lab.md).

## Fases del workflow

Copiar y marcar progreso:

```
Exploración del flujo:
- [ ] Fase 0 — Contexto y ventana objetivo
- [ ] Fase 1 — Ventana (shell de la app)
- [ ] Fase 2 — Objetos padre (contenedores)
- [ ] Fase 3 — Objetos hijo (controles interactuables)
- [ ] Fase 4 — Mapa de objetos documentado
- [ ] Fase 5 — Validación de localizadores
- [ ] Fase 6 — Reproducción del flujo
```

---

## Fase 0 — Contexto y ventana objetivo

**Objetivo:** saber en qué ventana trabajar **y cuál tiene el foco** antes de listar controles.

| Paso | Tool | Qué obtener |
|------|------|-------------|
| 0.1 | `list_windows` | Todas las ventanas del proceso — detectar modales ya abiertos |
| 0.2 | `get_focused_element` | Ventana/control con foco real del SO |
| 0.3 | `focus_window` | Traer la ventana correcta al frente (si hace falta) |
| 0.4 | `set_target_window` | Fijar alcance UIA para el flujo principal |
| 0.5 | `get_target_window` | Confirmar target MCP |

Si hay varias ventanas similares, anotar el título exacto o distintivo (ej. `* - Notepad` vs `Guardar como`).

**Antes de cada paso de Fase 6:** repetir 0.1–0.2 si la acción anterior pudo abrir o cambiar ventana. Si aparece un diálogo nuevo → sub-flujo modal (ver [patterns/active-window.md](patterns/active-window.md)); no continuar en el padre hasta cerrarlo.

---

## Fase 1 — Ventana (shell de la app)

**Objetivo:** entender el toolkit y si el árbol de accesibilidad es usable.

| Paso | Tool | Qué obtener |
|------|------|-------------|
| 1.1 | `detect_framework` | WPF, WinForms, Electron, Java Swing, etc. |
| 1.2 | `detection_health` | Backends disponibles (uia, flaui, msaa, ocr) |
| 1.3 | `observe_ui_tool` | Snapshot: framework, fingerprint, modales, menús, muestra del árbol |
| 1.4 | `ui_fingerprint` | Hash baseline para detectar cambios de pantalla |

**Decisión según framework:**

| Situación | Acción |
|-----------|--------|
| Árbol con muchos elementos nombrados | Seguir con UIA (`list_elements`, `spy_tree`) |
| Pocos elementos / app opaca | Planificar OCR (`find_text`) o `detect_visual_regions` |
| Java Swing | `check_java_bridge`; si falla, OCR como primario |
| Electron | Revisar hints de `detect_framework`; puede requerir flag de accesibilidad |
| Menús/tabs ocultos | Ir a Fase 2b (discovery) antes de buscar hijos |

---

## Fase 2 — Objetos padre (contenedores)

**Objetivo:** identificar la jerarquía de contenedores antes de los botones/campos.

Explorar con **profundidad baja** primero (`max_depth=2` o `3`).

| Paso | Tool | Parámetros sugeridos |
|------|------|---------------------|
| 2.1 | `list_elements` | `window_title`, `max_depth=2` |
| 2.2 | `spy_tree` | `window_title`, `max_depth=3` — detalle Spy |
| 2.3 | `list_elements` | Filtrar por rol padre: `MenuBar`, `TabControl`, `Pane`, `Group`, `Window`, `Dialog`, `Tree` |

**Padres típicos a identificar y documentar:**

- Ventana principal / diálogo modal
- Barra de menú (`MenuBar` → `MenuItem`)
- Pestañas (`TabControl` → `TabItem`)
- Paneles / grupos (`Pane`, `Group`, `Custom`)
- Árbol de navegación (`Tree` → `TreeItem`)
- Barras de herramientas (`ToolBar`)

Para cada padre, registrar en el mapa:

```
PADRE: <nombre lógico>
  role: ...
  name: ...
  automation_id: ...
  class_name: ...
  backend: uia|flaui|msaa
  hijos_esperados: [lista de controles del flujo]
```

### Fase 2b — Cuando los padres están ocultos

Si `list_elements` devuelve pocos nodos o el control está en menú desplegable / tab no seleccionado:

1. `plan_probes_tool` — probes ordenados con razón
2. `apply_probe_tool` — un probe a la vez (expandir menú, scroll, access key)
3. `observe_ui_tool` — re-observar tras cada probe
4. `discover_target_tool` — loop completo si el objetivo es un control concreto

No saltar a hijos hasta que el padre contenedor sea visible en el árbol.

---

## Fase 3 — Objetos hijo (controles interactuables)

**Objetivo:** localizar cada control con el que el flujo interactúa.

Subir profundidad solo dentro del padre ya identificado.

| Paso | Tool | Uso |
|------|------|-----|
| 3.0 | `discover_control_interaction` | **Antes de actuar**: estrategias ordenadas (tools, pasos, evitar). Obligatorio si role=Pane/Custom o `set_element_value` falló |
| 3.1 | `list_elements` | `max_depth=0` (árbol completo) o filtro `role="ComboBox"` / `Edit` / `Button` |
| 3.2 | `get_focused_element` | Saber qué control tiene foco en formularios |
| 3.3 | `spy_inspect` | Propiedades + discovery automático de interacción |
| 3.4 | `get_element_properties` | Inspector UIA de un elemento por name/automation_id |
| 3.5 | `element_at_point` | Solo si el usuario indica coordenadas; confirmar con highlight |
| 3.6 | `smart_find` | Cascada repo → nativo → OCR → visual (`agentic=false` en exploración) |

**Por cada paso del flujo del usuario**, definir:

```
PASO N: <acción humana descrita>
  OBJETO: <nombre lógico>
  localizador_primario: automation_id="..." / name="..." role="..."
  localizador_fallback: OCR "..." / repo_path="frmMain/btnSave"
  padre: <referencia al contenedor de Fase 2>
  verificación: highlight_element / screenshot(region)
```

Si un hijo no aparece en el árbol:
- Probar `find_text` para confirmar que es visible en pantalla
- `detect_visual_regions` para apps custom-painted
- `find_by_template_tool` si hay icono estable

### Patrones por framework

| Framework | Referencia |
|-----------|------------|
| **Roles UIA → leer / interactuar** | [patterns/control-catalog.md](patterns/control-catalog.md) (40 tipos) + [control-patterns-reference.md](patterns/control-patterns-reference.md) |
| WinForms (combos, lookup, MDI) | [patterns/winforms.md](patterns/winforms.md) |
| Win32 (menu bar cascada) | [patterns/win32-menubar.md](patterns/win32-menubar.md) |

Al identificar un control en Fase 3: consultar **control-catalog** por `role` y `patterns` de `spy_inspect` antes de elegir tool.

No documentar `automation_id` de un producto concreto aquí — usar la skill del producto (ver abajo).

### Lab y productos

| Contexto | Referencia |
|----------|------------|
| Evaluar MCP con una app | [evaluacion-lab.md](evaluacion-lab.md) — solo nombre; autodetect → `runs/.../discovered.yaml` |
| AST — Activities Manager | [ast-activities-manager](../../ast-activities-manager/SKILL.md) |

Al automatizar un **producto** conocido: metodología + skill de producto.  
Al **evaluar el MCP** con una app: metodología + evaluacion-lab + manifest de esa corrida.

---

## Fase 4 — Mapa de objetos documentado

Completar el template antes de ejecutar. Ver [object-map-template.md](object-map-template.md).

Entregable mínimo al usuario:

1. Ventana objetivo (`set_target_window` value)
2. Framework y backend recomendado
3. Tabla padres → hijos con localizadores
4. Secuencia de pasos con objeto resuelto por paso
5. Fallbacks OCR/visual donde UIA falla

---

## Fase 5 — Validación de localizadores

Por cada objeto del mapa, en orden padre → hijo:

1. `smart_find(name=..., role=..., window_title=..., highlight=true)`
2. Si falla: probar fallback documentado
3. `ui_fingerprint` antes y después de navegar — confirmar que la pantalla cambió
4. Para campos: `get_focused_element` después de foco/tab

**No avanzar a Fase 6** si algún localizador no resuelve de forma repetible.

---

## Fase 6 — Reproducción del flujo

Solo ahora ejecutar acciones, usando los localizadores validados.

**Narración obligatoria:** antes de **cada** tool de la tabla siguiente, publicar en chat el bloque «Voy a» (ver [action-narration.md](patterns/action-narration.md)). El observador debe poder seguir intención → acción en pantalla.

**Al abrir un diálogo:** el paso actual es la ventana nueva hasta que cierre. Scope `window_title` al diálogo; al salir, `list_windows` para confirmar que desapareció; recién entonces el siguiente paso es el formulario padre.

| Acción | Tool preferida | `capture` |
|--------|----------------|-----------|
| Clic en control accesible (secuencia) | `invoke_element` | n/a — sin screenshot |
| Clic con cascada | `click_element` | `false` (default) |
| Texto visible sin UIA | `click_text` | `false` |
| Escribir en campo | `set_element_value` o `click_element` + `type_text` | `false` |
| Combo / lista paginada | `list_control_items` + `select_control_item` | n/a |
| Fila en diálogo lookup | `select_lookup_row` o `select_control_item(double_click=true)` | n/a |
| Atajo de teclado | `send_keys` | n/a |
| Secuencia corta | `batch_actions` | `true` solo al final, o `false` + `screenshot()` aparte |
| Verificar resultado | `screenshot()` / `wait_for_change` / `ui_fingerprint` | explícito |

**Regla de velocidad:** durante ejecución, `capture=false` en todas las acciones. Un solo `screenshot()` al cerrar cada operación o al final del flujo.

Tras cada paso crítico: verificar con `ui_fingerprint` (rápido) o screenshot (solo si hace falta ver).

Al terminar: `focus_window(title="Claude")` o la ventana del usuario.

---

## Anti-patrones

- Actuar en el formulario padre mientras un modal/diálogo sigue abierto
- Asumir que `set_target_window` implica que esa ventana tiene el foco del SO
- Abrir Buscar / Guardar como / OK-Cancel y seguir el flujo principal sin cerrar el diálogo
- Reintentar el mismo control en el padre cuando el efecto no aparece — sin evaluar ventana activa primero
- Clicar por coordenadas estimadas desde screenshot downscaled
- `list_elements(max_depth=10)` en la primera pasada de Fase 2 — oculta la jerarquía de padres (en Fase 3 usar `max_depth=0` o filtro por rol)
- Buscar hijos antes de fijar ventana y padre contenedor
- Paralelizar tools AwdUI en Windows
- Saltar `highlight_element` cuando el localizador es ambiguo
- Usar `click`/`type_text` durante la fase de exploración
- `click_element` en bucle sin `capture=false` — cada screenshot cuesta segundos
- Usar `observe_ui_tool` en cada paso de Fase 6 — reservar para Fase 1 (snapshot inicial)
- Mezclar conocimiento de un producto (IDs, menús) en esta skill — usar la skill del producto

Patrones WinForms (lookup, combos, MDI): ver [patterns/winforms.md](patterns/winforms.md).

---

## Recursos

- Template de mapa: [object-map-template.md](object-map-template.md)
- Ejemplo genérico: [examples.md](examples.md) (Notepad)
- Ventana activa y modales: [patterns/active-window.md](patterns/active-window.md)
- Patrones WinForms: [patterns/winforms.md](patterns/winforms.md)
- Catálogo roles UIA (40 tipos): [patterns/control-catalog.md](patterns/control-catalog.md)
- Referencia patterns UIA: [patterns/control-patterns-reference.md](patterns/control-patterns-reference.md)
- Guía general AwdUI: `docs/AGENT_GUIDE.md`
- Productos: [ast-activities-manager](../../ast-activities-manager/SKILL.md)

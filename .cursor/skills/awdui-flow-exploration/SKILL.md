---
name: awdui-flow-exploration
description: >-
  Reproduce GUI flows methodically by first mapping programmatic object
  identification with AwdUI MCP: window, parent containers, then child
  controls. Use when automating desktop apps, replaying user flows, building
  test scripts, or when the user asks to explore UI objects before clicking.
---

# Exploración metódica de flujos UI (AwdUI)

Antes de ejecutar un flujo, **mapear e identificar objetos de forma programática**.
No clicar por coordenadas ni adivinar hasta tener un mapa estable ventana → padres → hijos.

## Reglas

1. **Explorar antes de actuar** — ningún `click`, `click_element` o `type_text` hasta completar el mapa del paso actual.
2. **Top-down estricto** — ventana → contenedores padre → controles hijo.
3. **Una ventana activa** — fijar target al inicio con `set_target_window` y mantenerla durante todo el flujo.
4. **Preferir identificadores estables** — en este orden: `automation_id` > `name`+`role` > `class_name` > OCR > coordenadas.
5. **Verificar antes de usar** — `highlight_element` o `smart_find` con `highlight=true` para confirmar el objeto correcto.
6. **Una tool a la vez** en Windows — no paralelizar llamadas AwdUI (COM/UIA).

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

**Objetivo:** saber en qué ventana trabajar antes de listar controles.

| Paso | Tool | Qué obtener |
|------|------|-------------|
| 0.1 | `list_windows` | Títulos parciales, posición, proceso |
| 0.2 | `focus_window` | Traer la app al frente (si hace falta) |
| 0.3 | `set_target_window` | Fijar ventana para auto-focus en cada acción |
| 0.4 | `get_target_window` | Confirmar target activo |

Si hay varias ventanas similares, anotar el título exacto o distintivo (ej. `* - Notepad` vs `Guardar como`).

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
| 3.1 | `list_elements` | `max_depth=5`, opcional `role="Button"` / `Edit` / `ComboBox` |
| 3.2 | `get_focused_element` | Saber qué control tiene foco en formularios |
| 3.3 | `spy_inspect` | Propiedades completas de un control candidato |
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

Solo ahora ejecutar acciones, usando los localizadores validados:

| Acción | Tool preferida | `capture` |
|--------|----------------|-----------|
| Clic en control accesible (secuencia) | `invoke_element` | n/a — sin screenshot |
| Clic con cascada | `click_element` | `false` (default) |
| Texto visible sin UIA | `click_text` | `false` |
| Escribir en campo | `set_element_value` o `click_element` + `type_text` | `false` |
| Atajo de teclado | `send_keys` | n/a |
| Secuencia corta | `batch_actions` | `true` solo al final, o `false` + `screenshot()` aparte |
| Verificar resultado | `screenshot()` / `wait_for_change` / `ui_fingerprint` | explícito |

**Regla de velocidad:** durante ejecución, `capture=false` en todas las acciones. Un solo `screenshot()` al cerrar cada operación o al final del flujo.

Tras cada paso crítico: verificar con `ui_fingerprint` (rápido) o screenshot (solo si hace falta ver).

Al terminar: `focus_window(title="Claude")` o la ventana del usuario.

---

## Anti-patrones

- Clicar por coordenadas estimadas desde screenshot downscaled
- `list_elements(max_depth=10)` en la primera pasada — oculta la jerarquía
- Buscar hijos antes de fijar ventana y padre contenedor
- Paralelizar tools AwdUI en Windows
- Saltar `highlight_element` cuando el localizador es ambiguo
- Usar `click`/`type_text` durante la fase de exploración
- `click_element` en bucle sin `capture=false` — cada screenshot cuesta segundos

---

## Recursos

- Template de mapa: [object-map-template.md](object-map-template.md)
- Ejemplo completo: [examples.md](examples.md)
- Guía general AwdUI: `docs/AGENT_GUIDE.md`

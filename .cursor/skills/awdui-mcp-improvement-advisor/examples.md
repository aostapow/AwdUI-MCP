# Ejemplos — AwdUI MCP Improvement Advisor

## Ejemplo de sesión (AST Time Report — turno real)

### Cronología resumida

1. Navegación a Time Report vía OCR (`TIMEREPORT`) — **funcionó** pero no era óptimo.
2. `list_elements(max_depth=5)` — **no** mostró `cboActividad`, `cboGrupo`, `cboConcepto`.
3. `list_elements(max_depth=10, include_offscreen=true)` — **sí** mostró combos con `automation_id`.
4. `spy_inspect(cboActividad)` — solo patterns `Value`, `LegacyIAccessible`; sin items.
5. Agente fue a OCR/coordenadas en lugar de `repo_action` Select o botón `Abrir`.
6. `find_text` con `window_title="Carga de Horas..."` — warning: ventana hija no matchea.
7. Timeouts en `observe_ui_tool`, `ui_fingerprint` (45s–280s).

### Clasificación de fricciones

| Fricción | tipo_gap | Propuesta |
|----------|----------|-----------|
| OCR antes de `role=ComboBox` | `routing_tool` | L4 skill: tras Fase 2, filtrar combos |
| Combos no visibles con depth 5 | `deteccion` | L3: escalar depth o default WinForms |
| Items de combo no listables | `tool_gap` | L4: nueva tool `list_combo_items` |
| Ventana hija no en scope OCR | `deteccion` | L4: resolver MDI en `window_title` |
| Timeouts observación | `performance` | L3: lazy screenshot en observe |
| Usuario preguntó por lectura programática | `ejecucion` | Ya existía la vía UIA — no proponer |

---

## Plantilla Tipo A — mejora_skill

```markdown
# Escalar detección de combos WinForms antes de OCR

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-07-07 01:15:00 |
| **Skill objetivo** | awdui-flow-exploration |
| **Tipo de gap** | routing_tool |
| **Nivel** | L4 |

## Resumen

**Problema:** En formularios WinForms anidados, el agente usa OCR cuando los ComboBox
ya son accesibles vía UIA con `automation_id`, si se lista con profundidad y filtro de rol.

**Solución:** Agregar en Fase 3 un paso obligatorio `list_elements(role="ComboBox")`
antes de cualquier `find_text`/`click_text` en campos de formulario.

**Dónde:** Fase 3 — Objetos hijo, tabla de herramientas.

## Texto propuesto

### Combos y listas WinForms (antes de OCR)

Tras identificar el panel del formulario (`Pane` / `Group` padre):

1. `list_elements(role="ComboBox", max_depth=10, include_offscreen=true)`
2. Registrar `automation_id` de cada campo en la **skill del producto** (no en la genérica)
3. Interactuar con `repo_action(method="Select", …)` o `set_element_value` en el Edit hijo
4. Solo si Select falla → botón `Abrir` / `btnBuscar` del lookup
5. OCR solo si el paso 1 devuelve 0 combos

## Criterio de aceptación

- [ ] Texto sin nombres de app del turno
- [ ] Cross: aplica a cualquier WinForms con TableLayoutPanel
```

---

## Plantilla Tipo B — mejora_tool

```markdown
# Tool list_combo_items

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_tool |
| **Estado** | propuesta |
| **Tool afectada** | (nueva) list_combo_items |
| **Tipo de gap** | tool_gap |
| **Nivel** | L4 |

## Resumen

**Problema:** WinForms ComboBox expone Value pero no hijos hasta expandir; el agente
no puede leer opciones ni seleccionar por substring sin OCR.

**Solución:** Tool que expande el combo, lista items vía UIA/MSAA, y opcionalmente selecciona.

## Spec propuesta

\`\`\`json
{
  "name": "list_combo_items",
  "parameters": {
    "automation_id": "required",
    "window_title": "optional parent window",
    "filter": "optional substring",
    "select": "optional exact/partial match",
    "max_items": 200
  }
}
\`\`\`

**Comportamiento:**
1. Resolver combo por `automation_id`
2. Intentar ExpandCollapse; si falla, enviar Alt+Down
3. Listar `ListItem` descendants
4. Si `select` presente → SelectionItem.Select o click item

**Módulos:** `uia_backend.py`, `repo_action.py` (_select_uia reuse)

## Criterio de aceptación

- [ ] Test pytest con WinForms fixture o mock
- [ ] Documentado en AGENT_GUIDE.md
```

---

## Plantilla Tipo C — mejora_codigo

```markdown
# Resolver ventanas hijas MDI en window_title

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Módulo** | tools/target_window.py, tools/ocr.py |
| **Tipo de gap** | deteccion |
| **Nivel** | L4 |

## Resumen

**Problema:** OCR y algunas tools con `window_title` parcial no encuentran ventanas
hijas embebidas (ej. formulario dentro de ventana principal del proceso).

**Solución:** Si no hay match exacto, buscar ventana hija cuyo proceso coincida con
el target y cuyo título parcial matchee; usar rect de la hija para scope OCR.

## Cambio propuesto (pseudodiff)

- En resolución de ventana: fallback `child_windows(process=target_pid, title_contains=…)`
- En `find_text`: si warning "No window matching", reintentar con hijos del target
- Exponer en respuesta qué ventana se usó para scope (debug)

## Criterio de aceptación

- [ ] `tests/test_window_scope.py` con ventana padre+hija simulada
- [ ] Sin regresión en `set_target_window` existente
```

# Win32 MenuItem: fallback bbox cuando InvokePattern falla

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | aplicada |
| **Fecha** | 2026-09-06 18:33:22 |
| **Usuario sesión** | ariel.ostapow |
| **Tool afectada** | click_element, invoke_element |
| **Módulo** | tools/ui_automation.py, detection/backends/uia_backend.py |
| **Tipo de gap** | tool_gap |
| **Nivel** | L4 |
| **MCP versión** | v0.4.0 |

## Resumen

**Problema:** En menús contextuales Win32 (y algunos submenús de barra), `list_elements`
expone `MenuItem` (Cortar, Copiar, Pegar) con bbox válido, pero `click_element` /
`invoke_element` fallan con InvokePattern. Si el elemento es «identificable» por propiedades,
`click_element` devuelve *coordinate click skipped for identifiable controls* y el agente debe
calcular manualmente el centro del bbox (`click` en 282,115 tras `list_elements`).

**Solución:** Tras fallo de Invoke en `role=MenuItem`, intentar clic en centro vía
`element_screen_bbox` (misma ruta que `highlight_element` / `click-at-highlight-coords`)
antes de error final. Opcional: parámetro `allow_coordinate_fallback=true` (default true para
MenuItem). Documentar en `control-catalog.md` fila MenuItem: «si Invoke falla en popup, bbox
center es esperado».

**Dónde:** `ui_automation.py` (`do_click_element`, `_try_invoke_click`), simétrico en
`do_invoke_element`; tests pytest; `docs/MCP_TOOLS_REFERENCE.md`.

## Contexto del turno

- Harness Notepad NP-21..30; **NP-24 met** y **NP-25 met** en este turno.
- NP-25: menú contextual con `list_elements(role=MenuItem)` → Cortar/Copiar/Pegar visibles;
  `invoke_element`/`click_element` en Copiar → InvokePattern fail; éxito con clic manual en
  coords derivadas del bbox de `list_elements`.
- NP-24: bloqueo inicial por `Ctrl+A` (Abrir) — resuelto con atajo de producto `Ctrl+E`; no es
  scope de este cambio (ver propuesta skill atajos locale).
- Skills: `awdui-mcp-objective`, `notepad`. MCP v0.4.0.

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| MenuItem contextual Invoke fail + coords skipped | tool_gap | L4 | Sí (este archivo) |
| Ctrl+A abre modal Abrir Win11 ES | routing_tool / sintoma_app | L1 | Skill producto ya documenta; ver skill atajos |
| focus_window insuficiente sin clic editor | entorno | L3 | Skill win32 cliente focus (propuesta separada) |
| drag select BETA en NP-25 | ejecucion | L2 | NP-13 met; sin cambio MCP |

Código actual (`ui_automation.py` ~1009–1018): `_identifiable_by_properties(elem)` bloquea
fallback coordenado aunque Invoke falle. Los `MenuItem` de popup suelen ser identificables
(name + role) pero no invocables de forma fiable vía UIA.

## Cambio propuesto (pseudodiff)

```python
# ui_automation.py — do_click_element, tras inv fallido:
if _identifiable_by_properties(elem):
    role = (elem.get("role") or "").lower()
    if role == "menuitem":
        timer.start("act")
        center_x, center_y = _click_coords(elem, window_title)
        click_result = do_click(center_x, center_y)
        timer.end()
        return _finish_action_with_verify(
            timer,
            {
                "success": True,
                "element": elem,
                "method": "MenuItem_bbox_fallback",
                "clicked_at": {"x": center_x, "y": center_y},
            },
            ...
        )
    return timer.attach({
        "success": False,
        "error": "Element found by properties but InvokePattern failed; coordinate click skipped ...",
        ...
    })
```

```python
# do_invoke_element — si Invoke falla y role=MenuItem, delegar a bbox click con method anotado
# o retornar hint: "use click_element with allow_coordinate_fallback"
```

## Test de abstracción (L4)

Aplica a menús contextuales Win32 (`notepad.exe`, `mspaint.exe`, shell, apps legacy) y
submenús donde Invoke es flaky. No depende de automation_ids de Notepad.

## Verificación de duplicados

- **Relacionada, no duplica:** `20260905_210300_click-element-selectionitem-datitem.md` (DataItem/
  Calendar SelectionItem — distinto pattern).
- **Precedente aplicado:** `20260707_024700_click-at-highlight-coords.md` (`element_screen_bbox`).
- **No duplica:** `notepad/gaps/mcp-improvements.md` fila «click_element MenuItem Edición FAIL»
  (menú bar top-level; misma raíz Invoke+bbox, esta propuesta cubre ambos casos).

## Esfuerzo observado

NP-25: al menos un reintento invoke/click + paso manual coords; flujo met pero fricción
estructural repetible en cualquier menú contextual Win32.

## Criterio de aceptación

- [ ] `tests/test_menuitem_bbox_fallback.py`: mock MenuItem identificable, Invoke fail → click OK.
- [ ] Live Notepad NP-25: `click_element(name="Copiar", role="MenuItem")` tras menú contextual
  sin `click(x,y)` manual.
- [ ] Sin regresión: botones con Invoke OK siguen usando InvokePattern (no bbox innecesario).
- [ ] `docs/MCP_TOOLS_REFERENCE.md` § `click_element` / `invoke_element` documenta excepción MenuItem.

## Beneficios futuros

- NP-25 y NP-14 ejecutables sin coords manuales del agente.
- Menos fricción en harness Win32 y apps sin skill de producto detallada.
- Alinea comportamiento con mensaje del catálogo («evitar coords si hay Invoke») con excepción
  documentada para MenuItem popup.

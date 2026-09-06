# list_elements: filtro within_automation_id para popups Calendar

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-05 21:03:01 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | detection/orchestrator.py, detection/backends/uia_backend.py, tools/ui_automation.py |
| **Tool afectada** | list_elements, find_element |
| **Tipo de gap** | performance |
| **Nivel** | L4 |
| **Impacto** | medio |
| **MCP versión** | v0.2.1 |

## Resumen

**Problema:** Con `CalendarView` abierto en Calculadora Fecha, `list_elements` tardó **5–6 s**
(⚠ SLOW) y devolvió `DataItem` de días con coordenadas que **contaminan** el inventario
(elementos fuera del popup calendario / mezcla con shell taskbar en coords). El scope por
ventana objetivo (`element_scope.py`, propuesta `124501` aplicada) no acota subárboles de
flyout/popup que comparten proceso pero no el rect principal de la app.

**Solución:** Parámetro opcional `within_automation_id` (o `ancestor_automation_id`) en
`list_elements` y `find_element`: restringir walk UIA a descendientes del nodo resuelto
(ej. `CalendarView`, `DateDiff_FromDate` popup). Combinar con `role=DataItem` para listar
solo días del mes visible. Respuesta incluir `ancestor_scope`, `elements_before_filter`.
Performance: walk acotado evita barrido completo de ventana + dedupe sobre cientos de nodos.

**Dónde:** `uia_backend.list_elements`, `orchestrator.list_elements`, tool schema;
`docs/MCP_TOOLS_REFERENCE.md`.

## Contexto del turno

Date exhaustive: `DateDiff_FromDate` invoke abre calendario; agente listó/busco `DataItem` día
«1» con latencia alta. Scope ventana (`foreign_elements_removed`) no eliminó ruido de coords
erróneas en taskbar durante popup. Tras selección manual por coords, verificación FromDate/ToDate
y modos Sumar/Restar OK. PID reuse **4428/28452**.

## Cambio propuesto (pseudodiff)

```python
# ui_automation.py list_elements tool
within_automation_id: Optional[str] = None  # restrict walk to subtree

# uia_backend.py
def list_elements(..., within_automation_id: Optional[str] = None):
    root = resolve_window_root(window_title)
    if within_automation_id:
        anchor = find_by_automation_id(root, within_automation_id)
        if not anchor:
            return []
        root = anchor
    return walk_subtree(root, max_depth=max_depth, role=role, ...)
```

```python
# orchestrator return metadata
return {
    "elements": scoped,
    "ancestor_scope": within_automation_id,
    "walk_root": "CalendarView" if within_automation_id else "window",
    ...
}
```

**Uso agente (modo Fecha):**
```
invoke_element(automation_id="DateDiff_FromDate")
list_elements(role="DataItem", within_automation_id="CalendarView")
click_element(name="1", role="DataItem")  # tras fix 210300
```

## Verificación de duplicados

- **Extiende** `20260905_124501` (scope ventana/PID) — no duplica; aplica cuando popup válido
  está **dentro** del proceso pero el walk completo es ruidoso/lento.
- Distinto de `120900` dedup runtime_id (mismo árbol, duplicados).
- Distinto de `125200` calculator bleed por modo (filtro por modo activo vs ancestro popup).

## Test de abstracción

Cross-app: DatePicker WinUI, Combo dropdown items (`within_automation_id` del List),
flyout menús, diálogos modales hijos con `automation_id` conocido.

## Criterio de aceptación

- [ ] `tests/test_list_elements_ancestor_scope.py`: fixture árbol con 2 subárboles →
      `within_automation_id` devuelve solo hijos del ancestro.
- [ ] Live Calculadora: `list_elements(role=DataItem, within_automation_id=CalendarView)`
      < 2 s y sin coords fuera del rect del popup.
- [ ] Sin `within_automation_id`: comportamiento actual sin regresión.
- [ ] Documentado en `MCP_TOOLS_REFERENCE.md`.

## Beneficios futuros

- Inventario calendario y popups sin SLOW ni coords taskbar en respuesta.
- Menos tokens al agente (lista corta de días vs árbol completo).
- Patrón reutilizable para cualquier flyout con `automation_id` estable.

# filter_elements_to_scope: test integración coords UWP screen-space

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | aplicada |
| **Fecha** | 2026-09-06 03:10:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | detection/element_scope.py, detection/element_coords.py |
| **Tool afectada** | list_elements, ascii_ui_view |
| **Tipo de gap** | deteccion |
| **Nivel** | L4 |
| **Impacto** | medio |
| **MCP versión** | v0.2.1 |

## Resumen

**Problema:** `filter_elements_to_scope` eliminaba 26/34 botones de Calculadora UWP porque
`to_screen_coords` trataba coordenadas ya en espacio de pantalla (ej. `num1Button` x=112
< `visual.x`=122) como lógicas, las escalaba por DPI y el centro quedaba fuera del client
rect. `list_elements` y `ascii_ui_view` parecían "no exponer" controles que `spy_tree` sí
mostraba. El fix en `element_coords.py` (candidatos logical/physical/screen, pick por
centro en scope, fast-path columna izquierda) ya está aplicado; existe unit test
`test_screen_coords_left_edge_center_inside_visual`, pero `test_element_scope.py` **mockea**
`to_screen_coords` y no valida el pipeline completo.

**Solución:** Agregar test de integración en `tests/test_element_scope.py` (o
`test_element_coords.py`) que:

1. Use fixture Calculadora con `window_region` / `resolve_window_visual_rect` mockeados
   (valores del turno: visual x=122, num1Button raw x=112 y=848 w=98 h=64).
2. **No** parchee `to_screen_coords`.
3. Llame `filter_elements_to_scope` con `DetectedElement` role=Button y verifique que el
   botón se conserva (`kept==1`, `scoped_out==0`).
4. Opcional: batch de num0–num9 + operadores con coords del turno.

**Dónde:** `tests/test_element_scope.py`; criterio en `test-after-changes.mdc`.

## Contexto del turno

Usuario: «como que no los va a exponer, algo estás haciendo mal» — diagnóstico:
`spy_tree` ~264 elem / 104 botones vs merge UIA 55/34; tras scope filter solo ~8 botones
antes del fix. Tras fix: 44/46 elementos, 31 botones; `ascii_ui_view` success 44/30
rendered. Skills: awdui-mcp-objective, calculator-mcp-harness.

## Cambio propuesto (pseudodiff)

```python
# tests/test_element_scope.py
def test_filter_scope_keeps_uwp_screen_space_left_edge_button(monkeypatch):
    from detection.element_model import DetectedElement
    from detection.element_scope import filter_elements_to_scope

    monkeypatch.setattr(
        "detection.element_coords.window_region",
        lambda _t: {"x": 122, "y": 397, "w": 531, "h": 843},
    )
    monkeypatch.setattr("detection.element_coords._dpi_scale_for", lambda _t: 1.25)
    monkeypatch.setattr(
        "detection.element_scope.resolve_window_scope",
        lambda _t: {
            "window_title": "Calculadora",
            "visual": {"x": 122, "y": 397, "width": 531, "height": 843},
            "client": {"x": 122, "y": 397, "w": 531, "h": 843},
            "process_ids": {12345},
        },
    )
    elem = DetectedElement(
        role="Button", name="Uno", automation_id="num1Button",
        x=112, y=848, width=98, height=64, process_id=12345, framework_id="XAML",
    )
    kept, scoped_out = filter_elements_to_scope([elem], "Calculadora")
    assert scoped_out == 0
    assert len(kept) == 1
    assert kept[0].automation_id == "num1Button"
```

## Criterio de aceptación

- [x] Test falla si se revierte `_pick_coord_candidate` / fast-path columna izquierda
- [x] No mockea `to_screen_coords` en este caso
- [x] `pytest tests/test_element_scope.py -q` verde
- [ ] Cross-app: aplica a cualquier UWP con bbox ligeramente a la izquierda del visual rect

## Verificación duplicados

- Relacionado con `aceptadas/mejoras-codigo/20260905_124501_list-elements-target-window-scope.md`
  (scope de ventana — aplicada); este ítem cubre **normalización de coords dentro del scope**.
- Unit test `test_screen_coords_left_edge_center_inside_visual` ya cubre `to_screen_coords`
  aislado; no duplica, complementa pipeline.

## Beneficios futuros

Evita regresión silenciosa donde `list_elements` / `ascii_ui_view` pierden keypad UWP tras
cambios en DPI o candidatos de coords; el agente no vuelve a interpretar «UIA no expone
botones» cuando el árbol sí los tiene.

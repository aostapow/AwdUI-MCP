# list_elements: acotar árbol a ventana objetivo

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | aplicada |
| **Fecha** | 2026-09-05 12:45:01 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | detection/backends/uia_backend.py, detection/orchestrator.py, tools/target_window.py |
| **Tool afectada** | list_elements |
| **Tipo de gap** | deteccion |
| **Nivel** | L4 |
| **Impacto** | alto |
| **MCP versión** | v0.2.1 |

## Resumen

**Problema:** Con `set_target_window("Calculadora")`, `list_elements` puede devolver
`ListItem` y controles de **otras aplicaciones** (Cursor, Chrome, shell) mezclados
con nodos XAML de la Calculadora. Documentado en `state.json` →
`calculator_perfect_gaps` y `current_focus: list_elements_scope`. Contamina
inventarios agenticos, aumenta tokens y puede inducir clicks en controles ajenos.
**Distinto** de dedup intra-árbol (`20260905_120900`): aquí el problema es scope
de ventana/proceso, no duplicados del mismo control.

**Solución:** Tras resolver HWND de la ventana objetivo (`target_window` / `window_title`):

1. Filtrar elementos cuyo centro (`element_center_in_rect`) no caiga dentro del
   rect de la ventana objetivo (con margen configurable, reutilizar `element_coords`).
2. Opcional: filtrar por `process_id` del sidecar/spy cuando el backend lo expone.
3. Exponer metadatos: `scoped_to_window`, `foreign_elements_removed`, `window_rect`.
4. Si `include_offscreen=false` (default), excluir nodos fuera del rect además de
   flag UIA offscreen.

**Dónde:** `UIABackend.list_elements`, `DetectionOrchestrator.list_elements`;
tests en `tests/test_list_elements_scope.py`.

## Contexto del turno

Turno `settings_expander_gap` cerró expanders Settings; `state.json` deja
`list_elements_scope` como **siguiente foco** del ciclo Calculadora. El gap fue
identificado en `calculator_perfect_eval` (no reobservado en este turno, pero
bloquea `calculator_perfect: true` según skill `calculator-mcp-harness` § Sin
contaminación).

## Cambio propuesto (pseudodiff)

```python
# uia_backend.py — tras walk/merge, antes de dedupe
from detection.element_coords import element_center_in_rect, window_region

def _filter_to_target_window(elements, window_title: str | None) -> tuple[list, int]:
    region = window_region(window_title)
    if not region:
        return elements, 0
    kept, removed = [], 0
    for el in elements:
        if element_center_in_rect(el, region, margin=8):
            kept.append(el)
        else:
            removed += 1
    return kept, removed

# orchestrator.list_elements return:
return {
    "elements": scoped,
    "count": len(scoped),
    "foreign_elements_removed": removed,
    "scoped_to_window": window_title or get_target_window_title(),
    ...
}
```

```python
# ui_automation.py list_elements tool header:
if result.get("foreign_elements_removed"):
    header += f" ({result['foreign_elements_removed']} outside target window removed)"
```

## Verificación de duplicados

- **No duplica** `20260905_120900` (dedup runtime_id/IoU — mismo árbol).
- Relacionado con `mdi-window-scope` (aceptada) pero aplica a UWP + desktop mezclado.
- `hwnd_scope.validate_hwnd_in_target` existe en tests — reutilizar lógica.

## Test de abstracción

Cross-app: cualquier `set_target_window` con otras apps visibles (IDE, browser)
se beneficia; patrón WinForms MDI hijo también si el rect del padre acota hijos.

## Criterio de aceptación

- [ ] `tests/test_list_elements_scope.py`: fixture con 2 elementos, uno fuera del
      rect objetivo → solo el interno en respuesta; `foreign_elements_removed=1`.
- [ ] Live Calculadora con Cursor enfocado: `list_elements` no incluye `ListItem`
      de menús del IDE (muestreo manual o integración harness).
- [ ] Sin regresión cuando no hay `window_title` / target (comportamiento actual).
- [ ] `docs/MCP_TOOLS_REFERENCE.md` § `list_elements`: parámetro/comportamiento scope.
- [ ] Complementa dedup: aplicar scope **antes** de dedupe.

## Beneficios futuros

- Cumple criterio «Sin contaminación» de `calculator-mcp-harness`.
- Inventarios más cortos y seguros para el agente.
- Base para `find_element` / `smart_find` con mismo filtro de ventana.

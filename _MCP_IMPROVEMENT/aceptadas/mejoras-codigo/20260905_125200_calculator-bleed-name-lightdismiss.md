# calculator_mode_filter: bleed sin automation_id y LightDismiss visible

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | aplicada |
| **Fecha** | 2026-09-05 12:52:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | detection/calculator_mode_filter.py, detection/element_dedupe.py |
| **Tool afectada** | list_elements |
| **Tipo de gap** | deteccion |
| **Nivel** | L3 |
| **Impacto** | bajo |
| **MCP versión** | v0.2.1 |

## Resumen

**Problema:** Tras `calculator_mode_filter` (turno `calc_mode_tree_bleed`), `list_elements`
en modo Estándar elimina 4 ids de otros modos (`ActiveTracing`, etc.) vía firmas
`automation_id`, pero **persisten** nodos sin `automation_id` del panel Configuración
(ej. Hyperlink `GitHub` en `AboutContribute`, textos legales) y a veces `LightDismiss`
visible como overlay duplicado. Contamina inventarios y puede inducir clicks en enlaces
de About fuera de Settings.

**Solución:**

1. En `element_bleeds_calculator_mode`, si `automation_id` vacío y `active_mode != "Settings"`:
   - Filtrar `role` Hyperlink/Text cuyo `name` coincida con tokens Settings-only
     (`github`, `eula`, `privacy`, `services agreement`, `build version`, etc.).
2. Para `LightDismiss`: además de `not visible`, excluir de salida `list_elements` cuando
   `active_mode` no es un modo con flyout abierto (heurística: no hay hijos flyout visibles
   con `ToggleState On`, o bbox ocupa >90% del client rect de la ventana).
3. Tests unitarios: `test_element_bleeds_standard_rejects_github_name_only`,
   `test_lightdismiss_fullscreen_overlay_removed`.

**Dónde:** `detection/calculator_mode_filter.py`; opcional coordinar ranking en
`element_dedupe.py`; nota en `patterns/calculator-lab.md` § Configuración.

## Contexto del turno

Turno `calc_mode_tree_bleed`: nuevo `calculator_mode_filter.py` integrado en
`orchestrator.py`; spy merge con `visible_only=not include_offscreen`; live Estándar
`2+3=5` OK; header `4 mode-bleed removed`; `test_calculator_mode_filter` 4 passed.
Residual explícito del agente: `LightDismiss` / settings diag sin `automation_id`.

## Cambio propuesto (pseudodiff)

```python
# calculator_mode_filter.py
_SETTINGS_NAME_TOKENS = frozenset({
    "github", "eula", "privacy", "services agreement", "build version",
    "contribute", "feedback",
})

def element_bleeds_calculator_mode(elem, active_mode):
    ...
    if active_mode != "Settings" and not aid:
        name = (elem.name or "").lower()
        role = (elem.role or "").lower()
        if "hyperlink" in role or role == "text":
            if any(tok in name for tok in _SETTINGS_NAME_TOKENS):
                return True
    if aid == "LightDismiss":
        if not visible:
            return True
        if _lightdismiss_is_fullscreen_overlay(elem):
            return True
    ...
```

## Criterio de aceptación / tests

- [ ] `list_elements` en Estándar no lista Hyperlink `GitHub` ni textos About sin aid
- [ ] `LightDismiss` fullscreen overlay no aparece en salida cuando flyout cerrado
- [ ] Modo Settings sigue exponiendo `AboutEULA`, `FeedbackButton`, expanders
- [ ] `pytest tests/test_calculator_mode_filter.py -q` ≥6 passed
- [ ] Live: Estándar tras visitar Settings — inventario sin nodos About name-only

## Verificación duplicados

- Complementa `20260905_120900` (dedup por aid) y filtro aid-based de este turno
- No duplica `20260905_124501` (scope ventana/proceso)
- `calculator-lab.md` ya documenta `GitHub` sin aid — esta propuesta **implementa** el filtro

## Beneficios futuros

- Inventarios agenticos más limpios en Calculadora tras navegar Settings
- Patrón reutilizable en otras apps WinUI NavView con pane inactivo en memoria UIA

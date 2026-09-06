# expand_element: verificar hijos y chevron interno en SettingsExpander UWP

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-05 21:10:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | tools/ui_automation.py, detection/element_coords.py, tools/spy_bridge.py |
| **Tool afectada** | expand_element |
| **Tipo de gap** | deteccion |
| **Nivel** | L4 |
| **Impacto** | medio |
| **MCP versión** | v0.2.1 |

## Resumen

**Problema:** Tras `expand_element(automation_id="AppThemeExpander", fallback_click=true)` el
fast-path reporta éxito en **~280 ms** (HeaderClick), pero los `ThemeRadioButtons` y los
`LightThemeRadioButton` / `DarkThemeRadioButton` / `SystemThemeRadioButton` **no aparecen**
en UIA hasta un segundo click en el **chevron interno** del expander (borde derecho del
header, ej. bbox ~(360,510)). El mismo patrón afecta `AboutExpander`: `AboutBuildVersion`
sí es visible, pero links legales (`AboutEULA`, `AboutControlServicesAgreement`,
`AboutControlPrivacyStatement`) quedan ocultos sin el chevron interno. El agente escaló a
coordenadas manuales pese a tener routing correcto (`expand_element` antes de coords).

**Solución:** Extender `do_expand_element` con verificación post-expand opcional:

1. Parámetro `verify_children: list[str] | null` — `automation_id` esperados tras expandir.
2. Tras HeaderClick / ExpandCollapse exitoso, `list_elements` scoped al padre o
   `spy_inspect` de cada `verify_children` (timeout ≤500 ms).
3. Si hijos ausentes y el padre es `_looks_like_uwp_expander`:
   - Buscar dentro del bbox del expander un `Button` / `Toggle` con `ExpandCollapse` o
     nombre vacío en el **tercio derecho** del header (`_expand_element_inner_chevron_click`).
   - Reintentar verificación de hijos; incluir en respuesta
     `{ nested_chevron_click: true, verify_children_found: [...] }`.
4. Si sigue fallando: `success=false`, `code=children_not_revealed`,
   `hint="inner chevron required; pass verify_children or click nested expand control"`.

## Evidencia adicional — turno `calculator_perfect_spy_tree_gate_complete` (2026-09-05 21:20)

- Workaround **confirmado en vivo**: inner chevron click en AboutExpander → links legales
  `AboutEULA`, `AboutControlServicesAgreement`, `AboutControlPrivacyStatement` visibles en UIA.
- Gate G3 cerrado con coords `(360,730)` — refuerza necesidad de `verify_children` +
  `_expand_element_inner_chevron_click` automático para eliminar escalada manual.
- Propuesta sigue **pendiente**; no bloquea `calculator_perfect` pero sí fricción en Settings.

**Dónde:** `ui_automation.py` (`do_expand_element`, helpers bbox),
`MCP_TOOLS_REFERENCE.md` § `expand_element`, `calculator-lab.md` § Configuración.

## Contexto del turno

Turno `calculator_exhaustive_act_verify` — pantalla Settings (cierre exhaustive):

- `SettingsItem` SelectionItem **549 ms** → header «Configuración» OK.
- `AppThemeExpander`: `expand_element` fast-path **280 ms** → radios **ocultos** hasta click
  chevron interno **(360,510)**; luego `LightThemeRadioButton` / `DarkThemeRadioButton` /
  `SystemThemeRadioButton` invoke verify ✓ **695–770 ms**.
- `AboutExpander` expand **278 ms** → `AboutBuildVersion` `11.2607.0.0` OK; links legales
  **no en UIA** sin expand interno (gap documentado en turno).
- `FeedbackButton` invoke **476 ms** offscreen OK; `GitHub` Hyperlink encontrado;
  `BackButton` → header modo Fecha verificado.
- Tarea `calculator_exhaustive_act_verify` marcada **done** con workaround coords en chevron.

Skills leídas: `awdui-mcp-objective`, `calculator-mcp-harness` (no `awdui-flow-exploration`).

## Cambio propuesto (pseudodiff)

```python
# ui_automation.py
def do_expand_element(
    ...,
    fallback_click: bool = False,
    verify_children: Optional[list[str]] = None,
) -> dict:
    result = _expand_outer(...)  # existing fast-path / ExpandCollapse chain
    if not result.get("success") or not verify_children:
        return result

    missing = _children_not_in_tree(verify_children, parent_aid=automation_id, window_title=window_title)
    if not missing:
        result["verify_children_found"] = verify_children
        return result

    if _looks_like_uwp_expander(elem_dict):
        inner = _expand_element_inner_chevron_click(elem_dict, window_title)
        result["nested_chevron_click"] = inner.get("success", False)
        missing = _children_not_in_tree(verify_children, ...)

    if missing:
        return {
            **result,
            "success": False,
            "code": "children_not_revealed",
            "missing_children": missing,
            "hint": "UWP SettingsExpander may need inner chevron; retry with verify_children",
        }
    result["verify_children_found"] = verify_children
    return result
```

```python
def _expand_element_inner_chevron_click(elem_dict: dict, window_title: str | None) -> dict:
    """Click right-edge chevron inside SettingsExpander bbox (not full header)."""
    bbox = element_screen_bbox(elem_dict)
    x = bbox["right"] - max(12, bbox["width"] * 0.08)
    y = (bbox["top"] + bbox["bottom"]) // 2
    return do_click_at(x, y, window_title=window_title)  # or find Button in right third
```

**Uso Calculadora Settings:**

```json
{
  "automation_id": "AppThemeExpander",
  "fallback_click": true,
  "verify_children": ["LightThemeRadioButton", "DarkThemeRadioButton"]
}
```

## Verificación de duplicados

- **Complementa** `20260905_123601` (outer HeaderClick) y `20260905_124500` (fast-path) —
  ambas **aplicadas**; no duplica outer expand.
- **Distinto** de `20260905_123600` (routing control-catalog / AGENT_GUIDE drift).
- **Distinto** de stale cache `20260905_120902` (entorno PID — ampliado en paralelo).
- Sin propuesta abierta previa sobre chevron **interno** post-`expand_element`.

## Test de abstracción

Cross-app: paneles Configuración WinUI / UWP con `SettingsExpander` anidado (Calculadora,
Configuración Windows, apps WinUI 3 con `NavigationView` settings) — no síntoma puntual
si el patrón «outer header + inner chevron» se repite en otros expanders Group.

## Criterio de aceptación

- [ ] `tests/test_expand_element.py`: mock SettingsExpander — outer click OK, hijos ausentes,
      inner chevron mock → `verify_children_found`.
- [ ] Live Calculadora: `expand_element(AppThemeExpander, fallback_click=true,
      verify_children=["LightThemeRadioButton"])` sin coords manuales → SelectionItem visible.
- [ ] Live: `AboutExpander` + `verify_children=["AboutEULA"]` → hyperlink en árbol sin coords.
- [ ] Respuesta incluye `nested_chevron_click` cuando aplica.
- [ ] `MCP_TOOLS_REFERENCE.md` § `expand_element`: param `verify_children`, código
      `children_not_revealed`.
- [ ] `calculator-lab.md` § Configuración: quitar implicación de que un solo
      `expand_element` basta; documentar `verify_children` o verificación post-expand.

## Beneficios futuros

- Settings Calculadora 100% programático sin coordenadas improvisadas en chevron interno.
- Patrón reutilizable para expanders UWP de dos niveles (header + chevron).
- El agente recibe señal estructurada (`children_not_revealed`) en lugar de fallos opacos
  en `invoke_element` sobre radios inexistentes en árbol.

## Esfuerzo observado

- Outer expand fast-path: **280 ms** (OK técnico, contenido no revelado).
- Recovery manual chevron coords + theme invokes: **695–770 ms** cada radio.
- About links: gap no resuelto en turno (solo `AboutBuildVersion` leído).

## Evidencia adicional — gate calculator_perfect (2026-09-05 21:10)

Reassess gate mantiene **About legal links** como bloqueador explícito en
`calculator_perfect_gaps` (`AboutEULA`, `AboutControlServicesAgreement`,
`AboutControlPrivacyStatement` sin UIA tras expand outer). Settings exhaustive marcado `met`
con workaround chevron interno; **calculator_perfect=false** hasta `verify_children` en
`AboutExpander` exponga hyperlinks o propuesta aplicada. Prioridad gate G3 en skill
`20260905_211201_calculator-perfect-gate-checklist.md`.

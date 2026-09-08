# expand_element: verify post-chevron sin doble list_elements profundo

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-06 20:14:30 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | `tools/ui_automation.py` (`_expander_contains_role`, `_expand_element_fallback_header_click`) |
| **Tool afectada** | expand_element |
| **Tipo de gap** | performance |
| **Nivel** | L4 |
| **Impacto** | medio |
| **MCP versión** | v0.4.0 |

## Resumen

**Problema:** Tras el fix CAL-20 (ChevronClick + banda vertical en
`_expander_contains_role`), `expand_element(AppThemeExpander, fallback_click=true)` **funciona**
pero tarda **16664 ms** (SLOW). La verificación post-click invoca hasta **dos** pasadas de
`do_list_elements(max_depth=12, include_offscreen=false)` sobre **toda la ventana** — una por
`RadioButton`, otra por `ListItem` — en lugar de un barrido acotado al subtree del expander.

**Solución:** (1) Unificar roles en una sola pasada
`_expander_contains_roles(parent, roles=("RadioButton", "ListItem", "Hyperlink"))`.
(2) Acotar el listing al ancestro del expander (`automation_id` padre + banda vertical ya
calculada) vía filtro espacial en el walker o `list_elements` con scope por `runtime_id` /
subárbol del padre. (3) Reutilizar el listing del paso `_try_expand_via_interactive_child`
(`max_depth=6`) cuando el chevron ya reveló hijos visibles. (4) Parámetro opcional
`verify_expand: bool = true` (default) con presupuesto `verify_max_ms` (default 1500) para
modo fast cuando el caller verifica aparte. (5) Exponer `verify_ms` y `verify_method` en la
respuesta para diagnóstico agentico.

**Dónde:** `ui_automation.py`, tests `tests/test_expand_element.py`,
`docs/MCP_TOOLS_REFERENCE.md` § `expand_element`, `calculator-lab.md` § Configuración (timing
esperado <3s).

## Contexto del turno

Turno `CAL-20-retest` tras fixes P1 SelectionItem verify + expand UWP:

| Paso | Timing | Resultado |
|------|--------|-----------|
| SettingsItem verify (Header) | 254 ms | OK |
| AppThemeExpander expand (ChevronClick) | **16664 ms** | OK funcional, SLOW |
| DarkThemeRadioButton verify | 454 ms | OK (nested `SelectionItem.is_selected.Value`) |
| SystemThemeRadioButton verify | 481 ms | OK |
| CAL-20 | met | WARN expand 16s |

Fixes aplicados en el mismo turno (no re-proponer):

- `run_selection_item_verify`: Header.changed primero si `pre_header`; unwrap
  `SelectionItem.is_selected.Value`; RadioButton sin check Header.
- `wait_tools` isSelected para valor anidado.
- MSAA `list_elements(window_handle=...)`.
- `expand_element`: `_try_expand_via_interactive_child`, ChevronClick bbox visible,
  `_expander_contains_role` con banda vertical, verify sin falso negativo.

`calculator_perfect=true`, `objective_met=true`; `state.json` marca P2 pendiente:
expand performance <3s.

Skills leídas: `awdui-mcp-objective`, `calculator-mcp-harness` (no `awdui-flow-exploration`).

## Cambio propuesto (pseudodiff)

```python
# ui_automation.py

def _expander_contains_roles(
    parent: dict,
    window_title: Optional[str],
    roles: tuple[str, ...] = ("RadioButton", "ListItem"),
    *,
    verify_max_ms: int = 1500,
) -> tuple[bool, dict]:
    """Single scoped pass; spatial band from parent bbox (existing logic)."""
    t0 = time.perf_counter()
    # Prefer shallow scoped walk under parent aid / runtime_id — NOT full window depth=12
    listing = _list_elements_under_parent(parent, window_title, max_depth=8)
    role_set = {r.lower() for r in roles}
    px, py, pw, ph = _parent_band(parent)
    band_bottom = py + max(ph * 3, ph + 180)
    for elem in listing:
        if (elem.get("role") or "").lower() not in role_set:
            continue
        if _point_in_band(elem, px, py, pw, band_bottom):
            return True, {"verify_ms": int((time.perf_counter() - t0) * 1000), "matched_role": elem.get("role")}
    return False, {"verify_ms": int((time.perf_counter() - t0) * 1000)}


def _expand_element_fallback_header_click(..., verify_expand: bool = True, verify_max_ms: int = 1500):
    ...
    if action == "expand" and verify_expand and _looks_like_uwp_expander(elem):
        opened, vmeta = _expander_contains_roles(elem, window_title, verify_max_ms=verify_max_ms)
        out["verify"] = vmeta
        if not opened and vmeta["verify_ms"] < verify_max_ms:
            out["success"] = False
            out["code"] = "expand_not_opened"
    return out
```

## Verificación de duplicados

- **Complementa** `20260905_211000` (chevron interno + verify hijos): funcionalidad base
  **implementada** este turno; param `verify_children` sigue pendiente en esa propuesta.
- **No duplica** `2026-09-06-notepad-list-elements-slow` (aplicada — fast path MenuItem Win32).
- **No duplica** `20260906_180100` (wall-clock discover/spy_walk).
- **Distinto** de stale cache `20260905_120902` — aquí el costo es verify estructural post-click.

## Test de abstracción (L4)

Cualquier UWP/WinUI `SettingsExpander` con verify post-expand vía barrido de roles hijos se
beneficia (Calculadora, apps WinUI 3 con paneles configuración). No es síntoma puntual de
Calculadora si el patrón «list_elements ventana completa × N roles» se repite.

## Esfuerzo observado

- CAL-20 funcional: verify SelectionItem **254–481 ms** (OK tras fix P1).
- Expand verify: **16664 ms** — bloquea loops agenticos en Settings aunque harness `met`.
- Turno anterior mismo gap: **11885 ms** (misma causa raíz probable).

## Criterio de aceptación

- [ ] Live Calculadora: `expand_element(AppThemeExpander, fallback_click=true)` < **3000 ms**
      p95 en 3 repeticiones con ventana ya en Settings.
- [ ] `tests/test_expand_element.py`: mock confirma **una** llamada a listing scoped (no dos
      `max_depth=12` ventana completa).
- [ ] Respuesta incluye `verify_ms` y `verify_method: "scoped_role_band"`.
- [ ] `verify_expand=false` omite barrido (ChevronClick only) para callers con verify externo.
- [ ] `MCP_TOOLS_REFERENCE.md` documenta params `verify_expand`, `verify_max_ms`.
- [ ] `state.json` `last_cycle.next` puede retirar P2 expand tras evidencia live.

## Beneficios futuros

- CAL-20 y Settings About/AppTheme repetibles en <3s sin degradar verify post-chevron.
- Patrón reutilizable para otras tools que verifiquen hijos tras acción (expand, flyout).
- Cierra gap «harness perfecto / calidad MCP operativa parcial» en `mcp_quality_note`.

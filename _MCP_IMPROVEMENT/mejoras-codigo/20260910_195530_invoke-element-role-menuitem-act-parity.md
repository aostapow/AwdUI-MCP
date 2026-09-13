# invoke_element: parámetro role y paridad act con click_element (MenuItem ExpandCollapse)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 19:55:30 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | `tools/ui_automation.py` (`do_invoke_element`, registro MCP `invoke_element`) |
| **Tool afectada** | invoke_element, click_element |
| **Tipo de gap** | tool_gap |
| **Nivel** | L4 |
| **Impacto** | alto |
| **MCP versión** | v0.4.0 (check_version 2026-09-10) |

## Resumen

**Problema:** Lab Escritorio **F-11** (Explorador — menú **Sistema** en barra de título Win32):
`invoke_element(name="Sistema")` falló **1753 ms** («sin Invoke pattern»); `click_element` con la
misma intención OK **1493 ms** vía **`ExpandCollapse.Expand`**. El flujo quedó `met` solo con
workaround agente. `click_element` filtra por **`role`** y usa `apply_hint_click_mode` +
`_try_invoke_click` → cascada UIA completa; `invoke_element` **no expone `role`**, resuelve con
`do_find_element` sin rol, y en fallo de patterns salta a **`_menuitem_bbox_click` solo si
`_is_menuitem(elem0)`** — si el match ambiguo no trae `role=MenuItem`, retorna fail en L939 sin
bbox ni hint de ExpandCollapse.

**Solución:**

1. Añadir parámetro opcional **`role`** a `invoke_element` / `do_invoke_element` (paridad
   `click_element`) y pasarlo a `do_find_element`.
2. Unificar el bloque **find → act** post-`do_find_element` con el de `do_click_element`:
   `apply_hint_click_mode` + `_try_invoke_click` (cascada Invoke→Toggle→SelectionItem→ExpandCollapse
   vía `uia_backend`) **antes** de `_menuitem_bbox_click`.
3. En respuesta fail cuando `patterns` listados incluyen **ExpandCollapse** y rol MenuItem:
   `hint`: «Use `expand_element` o `click_element(role=MenuItem)` — submenu sin Invoke».
4. Tests pytest + `docs/MCP_TOOLS_REFERENCE.md` § `invoke_element`.

**Dónde:** `ui_automation.py`; `tests/test_invoke_element_role_menuitem.py`; catálogo tools.

## Contexto del turno

- Lab `escritorio-windows-2026-09-10`, progreso **10/50 met**.
- F-11: `find_element` 606 ms OK → `invoke_element` fail → `click_element` ExpandCollapse OK →
  `list_elements(role=MenuItem)` Restaurar/Mover/Cerrar; Escape; evidencia `_10.png`.
- `improvements.jsonl`: fricción `invoke_element`, workaround click, `fix_in_cycle: not_attempted`.
- Skills: `awdui-mcp-automejora`, evaluación lab.

## Cambio propuesto (pseudodiff)

```python
# MCP tool + do_invoke_element — new optional role
def do_invoke_element(..., role: Optional[str] = None, ...):
    matches = do_find_element(
        name=name, automation_id=automation_id, role=role,
        window_title=window_title, ...
    )
    ...
    def _invoke_act():
        inv = _try_invoke_click(elem0, window_title)  # full cascade
        if inv and inv.get("success"):
            return inv
        return {"success": False}

    def _click_act():
        return _menuitem_bbox_click(...)  # existing bbox path

    result = apply_hint_click_mode(
        elem=elem0, click_mode=click_mode,
        invoke_fn=_invoke_act, click_fn=_click_act,
        identifiable_by_properties_fn=_identifiable_by_properties,
    )
```

```python
# Fail hint (when ExpandCollapse in elem0.patterns and not success)
if "expandcollapse" in patterns_norm and role_l == "menuitem":
    out["hint"] = (
        "Submenu MenuItem — try click_element(role=MenuItem) or expand_element; "
        "invoke without role may resolve wrong node"
    )
```

## Test de abstracción

Aplica a cualquier ventana Win32 con **menú Sistema** (`MenuItem` + ExpandCollapse, sin Invoke
usable): Explorador, Bloc de notas, diálogos con menú en barra de título — no específico del path
lab.

## Verificación duplicados

| Archivo | Relación |
|---------|----------|
| `aceptadas/.../20260906_183322_win32-menuitem-invoke-bbox-fallback.md` | Complementario — bbox tras Invoke fail; **no** cubre falta de `role` ni act parity |
| `mejoras-codigo/20260905_210300_click-element-selectionitem-datitem.md` | Paridad patterns en click — **ampliar** invoke en la misma dirección |
| `aceptadas/.../20260905_121300_invoke-expandcollapse-flyout.md` | Cascada ya en backend — gap es **resolución/find + pipeline invoke** |

## Beneficios futuros

- F-11 y flujos similares sin reintento manual invoke→click.
- Menos falsos fail cuando el agente sigue `flows.json` que dice «Invoke MenuItem Sistema».
- Hint accionable alineado con `control-catalog.md` (Expand=submenú).

## Criterio de aceptación

- [ ] `tests/test_invoke_element_role_menuitem.py`: mock/find con role MenuItem → method ExpandCollapse sin pasar por bbox si cascade OK.
- [ ] Live F-11 replay: `invoke_element(name="Sistema", role="MenuItem")` success < 2 s, method ExpandCollapse*.
- [ ] Fail sin role incluye hint ExpandCollapse cuando patterns lo indican.
- [ ] `python scripts/validate_tools_reference.py` verde tras doc `role` en invoke_element.

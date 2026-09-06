# spy_tree: acotar árbol a ventana objetivo (sin taskbar/Cursor)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-05 21:24:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | tools/ui_automation.py, tools/spy_bridge.py, awdui-spy-sidecar |
| **Tool afectada** | spy_tree |
| **Tipo de gap** | deteccion |
| **Nivel** | L3 |
| **Impacto** | bajo |
| **MCP versión** | v0.2.1 |

## Resumen

**Problema:** En gate `calculator_perfect_spy_tree_gate_complete`, `spy_tree(max_depth=12)` en
los 9 modos NavView cumplió el criterio de cobertura (240–283 nodos, Header OK), pero
`state.json` documenta contaminación residual: nodos de **taskbar** y **Cursor** mezclados en
algunos modos. El conteo de nodos de Calculadora es correcto, pero el árbol no está acotado
al HWND/proceso objetivo — dificulta diff automatizado y confunde agentes que buscan
`automation_id` por nombre en respuesta plana.

**Solución:**

1. Exponer en la tool MCP `spy_tree` los parámetros ya soportados por `spy_bridge.spy_tree`:
   `visible_only` (default `true` para gate) y `role_filter`.
2. Resolver `window_title` vía `set_target_window` / target activo y pasar al sidecar
   `walk_tree` con scope **subárbol de ventana** (mismo criterio que `list_elements` +
   `element_scope.py` post-`124501`).
3. Respuesta incluir metadatos: `{ scoped: true, target_hwnd, external_nodes_filtered: N }`.
4. Documentar en `MCP_TOOLS_REFERENCE.md`: gate depth 12 debe usar ventana objetivo, no desktop.

**Dónde:** `ui_automation.py` (`spy_tree` wrapper), `spy_bridge.py`, sidecar `walk_tree`,
`docs/MCP_TOOLS_REFERENCE.md`.

## Contexto del turno

- Turno `calculator_perfect_spy_tree_gate_complete` (MCP v0.2.1): 9/9 modos con
  `spy_tree depth=12`, Header + screenshot por modo; `calculator_perfect=true`.
- `calculator_perfect_gaps[1]`: «spy_tree depth 12 incluye nodos taskbar/Cursor en algunos
  modos (contaminación árbol; calculator nodes OK)».
- Skills: `awdui-mcp-objective`, `calculator-mcp-harness` (no `awdui-flow-exploration`).

## Cambio propuesto (pseudodiff)

```python
# ui_automation.py — spy_tree MCP tool
@server.tool()
def spy_tree(
    window_title: str = "",
    mode: str = "control",
    max_depth: int = 5,
    visible_only: bool = True,
    role_filter: str = "",
) -> str:
    from tools.spy_bridge import spy_tree, spy_available
    from tools.target_window import resolve_window_title
    wt = resolve_window_title(window_title)
    result = spy_tree(wt, mode, max_depth, visible_only=visible_only, role_filter=role_filter)
    ...
```

Sidecar: al recibir `window_title`, iniciar walk desde root de esa ventana, no `Desktop`.

**Nota consolidación (2026-09-05):** Propuesta **211200** (`post-act-verify-display-target`) **aplicada**
en el mismo ciclo post-gate — verify keypad redirige a `CalculatorResults`. Esta propuesta
212400 queda como mejora **residual L3** (ruido cosmético en conteo, no bloquea gate).

- **Consolidar tema** `window-scope` con `124501_list-elements-target-window-scope` (aceptada).
  Esta propuesta extiende el mismo principio a **`spy_tree`**, no duplica `list_elements`.
- Distinto de verify-target (`211200`) y expander chevron (`211000`).

## Test de abstracción

Cualquier app con gate «inventario UIA profundo» se beneficia de árbol scoped — WinForms MDI,
UWP flyouts, diálogos modales. No síntoma Calculadora puntual.

## Criterio de aceptación

- [ ] `tests/test_spy_tree_scope.py`: mock walk_tree recibe HWND de ventana target, no desktop.
- [ ] Live Calculadora: `spy_tree(max_depth=12)` sin nodos `Taskbar` / proceso Cursor en top-level.
- [ ] Parámetro `visible_only` documentado en `MCP_TOOLS_REFERENCE.md`.
- [ ] Gate harness: node_count estable ± nodos app-only.

## Beneficios futuros

- Diff de árbol entre modos sin ruido de shell.
- Agentes no confunden controles externos con IDs de la app bajo prueba.
- Alineación con scope ya aplicado en `list_elements`.

## Esfuerzo observado

- Gate 9 modos completado sin bloqueo por contaminación — gap **cosmético/diagnóstico**, no
  bloqueante para `calculator_perfect`. Fix mejora calidad de evidencia en regresiones futuras.

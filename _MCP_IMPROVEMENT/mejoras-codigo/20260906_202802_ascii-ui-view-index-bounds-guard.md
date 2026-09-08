# ascii_ui_view: guardas de índice en render (list index out of range)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-06 20:28:02 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | `detection/ascii_ui_render.py`, `tools/ascii_view.py` |
| **Tool afectada** | ascii_ui_view |
| **Tipo de gap** | tool_gap |
| **Nivel** | L4 |
| **MCP versión** | v0.4.0 |

## Resumen

**Problema:** En Teams TE-02, `ascii_ui_view` falla con `list index out of range` tras
`list_elements` exitoso (450 elementos, 7191ms). El agente pierde el mapa ASCII de
diagnóstico en apps Chromium con muchos nodos y coords heterogéneas (incl. contaminación
de ventanas vecinas).

**Solución:** (1) En `render_ascii_ui`, clamp `gx/gy/fx/fy` a `[0, cols-1]` / `[0, rows-1]`
antes de acceder `grid[gy][gx]`; omitir celdas fuera de rango con contador
`clipped_cells`. (2) Si `grid` vacío o `cols/rows < 4`, retornar error estructurado sin
traceback. (3) `do_ascii_ui_view`: capturar excepción, devolver
`{success: false, error, partial: true, elements_count}` en lugar de fallo MCP crudo.
(4) Opcional: parámetro `max_elements` (default 200) para truncar antes del layout en
árboles >500 nodos.

**Dónde:** `ascii_ui_render.py` (`_put_force`, `render_ascii_ui`, loop `paint_jobs`);
`ascii_view.py`; tests `tests/test_ascii_ui_view_bounds.py`.

## Contexto del turno

TE-02 discovery: `list_elements` 450 els SLOW; `spy_tree` 500 con filtros role OK;
`ascii_ui_view` FAIL `list index out of range`. `observe_ui_tool` y `ui_fingerprint` OK.
Skill `teams/flows/TE-02-discovery.md` lista `ascii_ui_view` como paso esperado.

Fix UWP coords (`031000` aplicada) no cubre IndexError en layout de grillas grandes.

## Cambio propuesto (pseudodiff)

```python
# ascii_ui_render.py
def _put_force(grid, gx, gy, ch):
    if not grid or gy < 0 or gy >= len(grid):
        return False
    row = grid[gy]
    if gx < 0 or gx >= len(row):
        return False
    if ch:
        row[gx] = ch
    return True

# render_ascii_ui — focus marker
if job["focused"] and inner_w >= 1 and inner_h >= 1:
    fx = min(max(gx1 + 1, 0), cols - 2)
    fy = min(max(gy1 + 1, 0), rows - 2)
    if _put_force(grid, fx, fy, "@"):
        ...
```

```python
# ascii_view.py
try:
    rendered = render_ascii_ui(...)
except IndexError as exc:
    return {
        "success": False,
        "error": f"ascii layout bounds: {exc}",
        "elements_count": len(elements),
        "hint": "retry with role=Button|Edit or max_depth lower",
    }
```

## Test de abstracción (L4)

Cualquier ventana con muchos elementos y bbox en borde del viewport (Electron, UWP denso,
Notepad con menús) — no específico de Teams.

## Verificación de duplicados

- `031000` (UWP screen coords) — **aplicada**; problema distinto (crash vs coords).
- Sin propuesta abierta para IndexError en ascii render.

## Esfuerzo observado

Paso TE-02 incompleto en mapa ASCII; agente continuó con `spy_tree` + role filters.

## Criterio de aceptación

- [ ] Fixture con elementos en coords extremas no lanza IndexError.
- [ ] Respuesta incluye `clipped_cells` cuando hay recorte.
- [ ] Teams-like tree mock (450 nodos) retorna `success: true` o error JSON sin stack.
- [ ] `tests/test_ascii_ui_view_bounds.py` en pytest verde.

## Beneficios futuros

- TE-02 y exploración Fase 2 genérica con `ascii_ui_view` confiable en apps pesadas.

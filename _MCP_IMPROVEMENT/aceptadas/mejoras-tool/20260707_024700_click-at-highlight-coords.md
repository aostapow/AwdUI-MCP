---
estado: aplicada
tipo_propuesta: mejoras-tool
tipo_gap: deteccion
nivel_abstraccion: L4
fecha: 2026-07-07
turno_ref: ast-carga-108082-fallida
implementado: 2026-07-07
---

| Campo | Valor |
|-------|-------|
| **Estado** | aplicada |

# Tool: `click_element` unificar coords con highlight

## Implementado

- `ui_automation._click_coords` y `repo_action._click_coords` usan `element_screen_bbox` (misma ruta que `highlight_element`) antes del fallback `click_coords`.
- Documentado en `docs/MCP_TOOLS_REFERENCE.md`.

## Módulos

`tools/ui_automation.py`, `tools/repo_action.py`, `tools/highlight.py`

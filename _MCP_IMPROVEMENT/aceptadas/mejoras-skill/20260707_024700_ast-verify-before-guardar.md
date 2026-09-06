---
estado: aplicada
tipo_propuesta: mejoras-skill
tipo_gap: routing_tool
nivel_abstraccion: L3
fecha: 2026-07-07
turno_ref: ast-carga-108082-fallida
implementado: 2026-07-07
---

| Campo | Valor |
|-------|-------|
| **Estado** | aplicada |

# AST Time Report: verificar combos y Guardar antes de cerrar

## Implementado en

- `.cursor/skills/ast-activities-manager/flows/time-report-hours.md`
- `.cursor/skills/ast-activities-manager/SKILL.md`

## Reglas clave

- `get_control_state` tras cada combo (grupo/concepto).
- `spy_inspect(btnGuardar)` → `is_enabled` antes de guardar.
- `highlight_element` antes de click en `btnBuscar` / `btnGuardar`.

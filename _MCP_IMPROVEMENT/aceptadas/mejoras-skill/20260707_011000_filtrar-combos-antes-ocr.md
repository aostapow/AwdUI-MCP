# Filtrar combos WinForms antes de OCR

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | aplicada |
| **Fecha** | 2026-07-07 01:10:00 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | awdui-flow-exploration |
| **Tipo de gap** | routing_tool |
| **Nivel** | L4 |
| **Impacto** | alto |

## Resumen

**Problema:** En formularios WinForms anidados (paneles dentro de ventanas hijas MDI),
el agente recurre a OCR y coordenadas aunque los ComboBox son accesibles con
`automation_id` (`cboActividad`, `cboGrupo`, `cboConcepto`, `cboHoras`) cuando
`list_elements` usa profundidad suficiente y filtro por rol.

**Solución:** Hacer obligatorio en Fase 3 un paso `list_elements(role="ComboBox",
max_depth=10, include_offscreen=true)` antes de `find_text`/`click_text` en campos
de formulario; documentar interacción vía `repo_action` Select y botón `Abrir` del lookup.

**Dónde:** Fase 3 — Objetos hijo; nueva subsección «Combos WinForms».

## Versiones MCP

| MCP | Versión | Nota |
|-----|---------|------|
| user-awdui | (consultar check_version) | Gap es de routing del agente, no de versión |

## Texto propuesto

### Combos WinForms (obligatorio antes de OCR)

Tras mapear el panel del formulario:

1. `list_elements(role="ComboBox", max_depth=10, include_offscreen=true)`
2. Anotar `automation_id` de cada combo del flujo
3. `spy_inspect(automation_id=…)` — ver patterns (`Value`, `ExpandCollapse`)
4. Seleccionar: `repo_action(method="Select", value="…")` o botón `Abrir`/`btnBuscar` si es lookup
5. OCR solo si el paso 1 devuelve 0 combos en el panel objetivo

## Criterio de aceptación

- [ ] Sin nombres de app específicos en texto_propuesto
- [ ] Cross: aplica a WinForms con TableLayoutPanel

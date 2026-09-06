# Combo editable: fallback type-ahead con verificación obligatoria

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-07-07 14:19:00 |
| **Usuario sesión** | carga horas AST Time Report |
| **Skill objetivo** | awdui-flow-exploration/patterns/winforms.md |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Impacto** | medio |

## Resumen

**Problema:** Cuando `list_control_items` devuelve 0 items y `select_control_item` falla
en ComboBox WinForms editables (`cboActividad`, `cboGrupo`, `cboConcepto`), el agente usó
click + type + Down + Enter. En `cboActividad` con código `108082`, el type-ahead seleccionó
`38608` (actividad incorrecta) porque el filtro por prefijo numérico es ambiguo. En
`cboGrupo`/`cboConcepto` el mismo patrón funcionó con substring textual.

**Solución:** Documentar en patrones WinForms el fallback type-ahead solo para búsqueda por
**substring textual** (no solo dígitos), siempre seguido de `get_control_state` /
`verified_value`. Para códigos numéricos ambiguos → lookup modal o `select_control_item`
tras expandir popup.

**Dónde:** `.cursor/skills/awdui-flow-exploration/patterns/winforms.md` — nueva subsección
tras «Combos (antes de OCR)».

## Contexto del turno

- `cboGrupo`/`cboConcepto`: `list_control_items` → 0; type-ahead `homologacion`/`calendario` → OK.
- `cboActividad`: type-ahead `108082` → selección incorrecta 38608; lookup posterior OK.

## Texto propuesto

### Fallback type-ahead (solo si UIA no lista items)

Cuando `list_control_items` y `select_control_item` fallan:

1. `click_element` en el combo (o `highlight_element` + click en centro).
2. `type_text` con **substring textual** del valor esperado (ej. `homologacion`, no solo `108`).
3. `send_keys` `down` + `enter` (o `select_control_item` si el popup ya es visible).
4. **Obligatorio:** `get_control_state` — `value` debe contener el término buscado.
5. Si el valor es numérico/código y el paso 4 no confirma el código exacto → **no** repetir
   type-ahead; usar botón lookup del combo o `list_control_items` tras `expand=true`.

**Anti-patrón:** tipear solo dígitos en combo editable de actividades/códigos sin verificar —
el autocompletado puede resolver a otro ítem con prefijo común.

## Verificación de duplicados

- `aceptadas/mejoras-skill/20260707_011000_filtrar-combos-antes-ocr.md` — UIA antes de OCR; no cubre fallback teclado ni verificación post-type-ahead.
- `aceptadas/mejoras-codigo/20260707_024700_combo-select-verify-no-set-value.md` — verificación en MCP para `select_control_item`; no documenta fallback manual del agente.

## Test de abstracción

- L3: aplica a cualquier WinForms ComboBox editable con autocompletado por prefijo.

## Beneficios futuros

- Evita selecciones silenciosamente incorrectas en combos de códigos.
- Estandariza el fallback que ya funcionó para grupo/concepto.

## Criterio de aceptación

- [ ] Subsección en `winforms.md` sin IDs de AST.
- [ ] Enlazada desde Fase 3 de `awdui-flow-exploration/SKILL.md` (una línea).

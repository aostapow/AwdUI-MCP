# AST Time Report: actividad directa en combo y verificación en gcGrillaHoras

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-07-07 14:19:00 |
| **Usuario sesión** | carga horas AST Time Report |
| **Skill objetivo** | ast-activities-manager |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Impacto** | medio |

## Resumen

**Problema:** El flujo documentado en `time-report-hours.md` inicia siempre con `btnBuscar`
(lookup), aunque `cboActividad` admite selección directa por código cuando
`select_control_item` / `list_control_items` funcionan. El agente probó combo directo,
falló con `set_element_value` (solo código), luego type-ahead sin verificar y eligió
actividad incorrecta (38608). Tras lookup, la carga fue exitosa. Además, la verificación
post-guardado buscó `gcGrillaActividades` en el formulario principal (no encontrado);
la fila guardada apareció en `gcGrillaHoras`.

**Solución:** Reordenar el flujo AST: intentar combo directo primero; lookup como fallback.
Documentar `gcGrillaHoras` como grilla de verificación en el formulario principal.
Prohibir type-ahead numérico sin verificar `Value` completo.

**Dónde:** `.cursor/skills/ast-activities-manager/SKILL.md` (mapa de objetos) y
`flows/time-report-hours.md` (pasos y verificación).

## Contexto del turno

- `list_control_items(cboActividad, 108082)` → 0 items; `set_element_value` → solo código.
- `select_control_item` falló; type-ahead eligió 38608 (incorrecto).
- Lookup `btnBuscar` → OK; horas, grupo, concepto OK con fallback teclado en combos.
- Usuario corrigió: no hace falta `btnBuscar` si el combo directo funciona.
- Verificación exitosa en `gcGrillaHoras` (fila 108082, 6 hs); `gcGrillaActividades` no en form principal.

## Texto propuesto

### Mapa de objetos — agregar / corregir

| Objeto lógico | automation_id | Notas |
|---------------|---------------|-------|
| Grilla horas cargadas (form principal) | `gcGrillaHoras` | Verificación post-guardado |
| Grilla resultados lookup (diálogo Buscar) | `gcGrillaActividades` | Solo con `window_title="Buscar"` |

### Flujo actividad (reordenado)

1. `list_control_items(cboActividad, filter_text=<código>)` o `select_control_item(cboActividad, value=<código>)`.
2. Verificar con `get_control_state(cboActividad)` que `value` contiene el código **y** texto descriptivo.
3. Si paso 1–2 fallan → lookup (`btnBuscar` → `teFind` → `btFind` → `select_lookup_row`).
4. **No** usar `set_element_value` en ComboBox dropdown.
5. **No** type-ahead con solo dígitos sin verificar; códigos parciales matchean otra actividad.

### Verificación post-guardado

- `list_control_items(gcGrillaHoras, filter_text=<código>)` en formulario Carga de Horas.
- `gcGrillaActividades` aplica solo al diálogo Buscar, no al form principal.

## Verificación de duplicados

- `aceptadas/mejoras-skill/20260707_024700_ast-verify-before-guardar.md` — cubre `btnGuardar`/`get_control_state`; no cubre orden actividad ni `gcGrillaHoras`.
- `aceptadas/mejoras-codigo/20260707_024700_combo-select-verify-no-set-value.md` — código MCP; este gap es routing/documentación AST.

## Test de abstracción

- L3: el patrón «combo con lookup opcional» y «grilla distinta en modal vs form» aplica a WinForms con lookup embebido; IDs son AST.

## Beneficios futuros

- Menos pasos cuando el código de actividad es conocido.
- Verificación post-guardado sin falso «control no encontrado».
- Evita selección errónea por type-ahead parcial.

## Criterio de aceptación

- [ ] `time-report-hours.md` lista combo directo antes de lookup.
- [ ] `SKILL.md` distingue `gcGrillaHoras` vs `gcGrillaActividades`.
- [ ] Sin regresión en reglas de `spy_inspect(btnGuardar)` ya aplicadas.

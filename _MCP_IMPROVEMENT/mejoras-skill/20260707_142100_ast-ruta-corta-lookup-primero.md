# AST Time Report: ruta corta — lookup actividad primero, no combo trial-and-error

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-07-07 14:21:00 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | `ast-activities-manager/flows/time-report-hours.md` |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Impacto** | alto |

## Resumen

**Problema:** El turno consumió **~45 llamadas AwdUI** para una sola fila (objetivo ~12–15).
El agente probó combo directo en `cboActividad` durante 10+ tools (list, set_value, select,
type-ahead erróneo) antes del lookup que funcionó en 4 tools. El usuario pidió combo directo,
pero UIA no expone items y type-ahead numérico es **peligroso** (seleccionó 38608).

**Solución:** Documentar **ruta corta** para actividad por código numérico:

1. Si el término es código numérico (`^\d+$`) → **lookup directo** (`btnBuscar` → `teFind` →
   `btFind` → `select_lookup_row`) sin intentar combo primero.
2. Combo directo solo si `list_control_items` devuelve ≥1 match **antes** de seleccionar.
3. **Nunca** `set_element_value` + `down` + `enter` en `cboActividad` sin verificar texto completo.
4. Grupo/concepto: un intento `select_control_item`; si falla → type-ahead documentado con verify.

**Dónde:** `flows/time-report-hours.md` sección «Atajos» y «Errores a evitar».

## Contexto del turno

| Fase | Tools aprox. | Resultado |
|------|--------------|-----------|
| Combo actividad (fallido) | ~12 | Actividad incorrecta 38608 |
| Lookup actividad | 4 | OK |
| Horas | 2 | OK |
| Grupo (manual) | ~8 | OK |
| Concepto (manual) | ~6 | OK |
| Guardar + verify | ~10 | OK (gcGrillaHoras) |
| **Total** | **~45** | Excesivo |

## Texto propuesto

### Ruta corta (una fila, código de actividad conocido)

```
btnBuscar → teFind (click+type si ValuePattern falla) → btFind
→ select_lookup_row(gcGrillaActividades, value=<código>)
→ set_element_value(cboHoras, ...)
→ select_control_item(cboGrupo) | typeahead fallback
→ select_control_item(cboConcepto) | typeahead fallback
→ spy_inspect(btnGuardar) → click
→ list_control_items(gcGrillaHoras, filter=<código>)
```

### Anti-patrón documentado

- No iterar combo actividad cuando `list_control_items` devuelve 0 en el primer intento.
- Códigos numéricos parciales en type-ahead matchean otra actividad.

## Verificación de duplicados

- `mejoras-skill/20260707_141900_ast-actividad-directa-verificar-grilla-horas.md` — propone combo primero; **esta propuesta lo refina**: lookup primero para códigos numéricos, combo solo con items UIA visibles. Considerar merge al implementar.

## Test de abstracción

- L3: patrón «lookup modal para IDs numéricos, combo para texto parcial» aplica a WinForms con lookup embebido.

## Beneficios futuros

- Turnos de carga de horas: ~15 tools en lugar de ~45.
- Menos riesgo de actividad incorrecta guardada.

## Criterio de aceptación

- [ ] `time-report-hours.md` incluye tabla de rutas por tipo de término (numérico vs texto).
- [ ] Estimación de tools documentada (ruta corta vs exploración).
- [ ] Merge o reconciliación con propuesta `141900` al aplicar.

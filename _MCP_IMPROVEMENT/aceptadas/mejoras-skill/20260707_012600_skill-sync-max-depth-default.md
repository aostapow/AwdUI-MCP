# Sincronizar skill con default list_elements full-tree

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | aplicada |
| **Fecha** | 2026-07-07 01:26:00 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | awdui-flow-exploration |
| **Tipo de gap** | deteccion |
| **Nivel** | L3 |
| **Impacto** | medio |

## Versiones MCP

| MCP | Versión | Nota |
|-----|---------|------|
| user-awdui | v0.2.1 | Código ya tiene `LIST_ELEMENTS_DEFAULT_MAX_DEPTH=0` en tree_depth.py |

## Resumen

**Problema:** La skill Fase 3 recomienda `max_depth=5` y anti-patrón desaconseja `max_depth=10` en primera
pasada. El servidor ya cambió el default a árbol completo (`0`). El agente del turno usó `max_depth=5`,
no vio combos, y escaló a OCR antes de probar `role="ComboBox"`.

**Solución:** Actualizar Fase 3 y anti-patrones para reflejar el default actual: sin `max_depth` el árbol
es completo; para mapeo inicial de padres seguir usando `max_depth=2–3`; para hijos en formularios
usar `role="ComboBox"` / `role="Button"` en lugar de subir depth ciegamente.

**Dónde:** Fase 3 tabla de tools; sección Anti-patrones; opcional nota en `docs/AGENT_GUIDE.md`.

## Texto propuesto

### Fase 3 — actualización

| Paso | Tool | Uso |
|------|------|-----|
| 3.1 | `list_elements` | Default sin `max_depth` = árbol completo. Para padres ya conocidos, filtrar por `role` (`ComboBox`, `Button`, `Edit`) antes de ampliar scope |
| 3.1b | `list_elements` | Si el árbol es muy grande, acotar con `max_depth=10` + `include_offscreen=true` solo dentro del panel padre identificado |

### Anti-patrones — reemplazar

- ~~`list_elements(max_depth=10)` en la primera pasada~~ → `list_elements` sin filtro de rol en formulario completo sin haber identificado el panel padre (Fase 2).
- Agregar: `list_elements(max_depth=5)` fijo en formularios anidados — los ComboBox suelen estar más profundo; preferir `role="ComboBox"`.

## Contexto del turno

`list_elements(max_depth=5)` no mostró `cboActividad`; `role="ComboBox"` sí. El mantenedor implementó
default full-tree en el mismo turno; la skill quedó desalineada.

## Test de abstracción

Aplica a cualquier WinForms con TableLayoutPanel / paneles anidados. No específico de AST.

## Verificación de duplicados

- Complementa `20260707_011000_filtrar-combos-antes-ocr.md` (routing OCR) sin duplicarlo — este artefacto
  cubre documentación del default de profundidad.
- Tema `max-depth` del manifiesto: consolidar al aplicar ambas propuestas skill.

## Criterio de aceptación

- [ ] Fase 3 y anti-patrones sin nombres de app del turno
- [ ] Menciona `role` filter como primera estrategia en formularios
- [ ] Coherente con `LIST_ELEMENTS_DEFAULT_MAX_DEPTH=0` en código

## Beneficios futuros

Agentes nuevos no repiten el error de `max_depth=5` cuando el servidor ya lista árbol completo por default.

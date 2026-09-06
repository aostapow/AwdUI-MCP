# Routing post-expand_element: control-catalog y AGENT_GUIDE

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-05 12:36:00 |
| **Skill objetivo** | awdui-flow-exploration/patterns/control-catalog.md, docs/AGENT_GUIDE.md |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Impacto** | medio |

## Resumen

**Problema:** Tras exponer `expand_element` y cascada ExpandCollapse en `invoke_element`
(turno `mcp_expand_element_tool`, MCP v0.2.1), `MCP_TOOLS_REFERENCE.md` ya documenta la
tool real, pero **`control-catalog.md`** y **`AGENT_GUIDE.md`** siguen referenciando
`invoke_pattern(ExpandCollapse)` y otras tools fantasma en la sección combos/patterns.
El agente puede elegir una API inexistente tras leer el catálogo de controles.

**Solución:** Sincronizar routing L3 en dos archivos:

1. **`control-catalog.md`** — árbol de decisión y tabla ExpandCollapse:
   - Reemplazar `invoke_pattern(ExpandCollapse)` → **`expand_element`** (ComboBox/TreeItem)
     o **`invoke_element`** (cascada incluye Expand).
   - Fila ComboBox: «expandir picker» → `expand_element` antes de `list_control_items`.
2. **`AGENT_GUIDE.md`** § Combos, patterns:
   - Quitar o marcar obsoleto bullet `invoke_pattern`.
   - Añadir: `expand_element` — ExpandCollapse atómico; `invoke_element` — cascada con Expand.

**Dónde:** `patterns/control-catalog.md` (líneas 21–28, 152), `docs/AGENT_GUIDE.md` (línea 84).

## Contexto del turno

Implementación `expand_element` + tests 3 passed + live conversores OK. Drift residual
ya anotado en `20260905_123100` criterios de aceptación; `validate_tools_reference` OK
pero no valida skills ni AGENT_GUIDE.

## Texto propuesto (control-catalog)

```markdown
ExpandCollapse (sin Invoke) → TreeItem / ComboBox UWP → expand_element → list_elements / list_control_items
```

Tabla patterns:

| ExpandCollapse | expand_state | expand/collapse | `expand_element`, `invoke_element` (cascada) |

## Verificación de duplicados

- Complementa (no duplica) `20260905_123100` criterio drift AGENT_GUIDE.
- `MCP_TOOLS_REFERENCE.md` ya correcto — no tocar.

## Criterio de aceptación

- [ ] Sin referencias activas a `invoke_pattern` en control-catalog ni AGENT_GUIDE (salvo nota histórica).
- [ ] Cross-app: ComboBox WinForms y TreeItem WinUI cubiertos sin nombre Calculadora.
- [ ] Enlace a `MCP_TOOLS_REFERENCE.md` § `expand_element`.

## Beneficios futuros

- Agente lee catálogo de controles y elige tool existente.
- Cierra drift docs post `docs_tools_sync` sin reintroducir tools fantasma.

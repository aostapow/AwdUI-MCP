# discover_flows subárbol — banda Dirección en edición (Edit, no find parcial)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 20:02:15 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | `awdui-mcp-automejora/references/evaluacion-lab.md` |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Versión MCP** | 0.4.0 |

## Resumen

**Problema:** En `discover_flows` **subárbol** tras re-invoke del entry **F-12** (SplitButton
«Todas las ubicaciones»), UIA abre modo edición en **Edit «Dirección»** (sin segmentos
`MenuItem` de ruta). El agente ya obtuvo foco útil con `get_focused_element`, pero igual ejecutó
`find_element(name="Temp", role="Button")` (**8967 ms** SLOW, hit) y `list_elements(role="SplitButton")`
(**9535 ms** SLOW) sobre la ventana completa para encolar **F-57..F-59**.

**Solución:** Bloque discover B3–B4 **barra de direcciones en edición** (complemento execute de
`20260910_195900_explorer-breadcrumb-flyout-verify-routing`):

1. Tras invoke del SplitButton padre: **`get_focused_element`** + `read_element` — si role `Edit`
   y nombre contiene «Dirección» / Address pattern → encolar **un** action de verificación
   (foco + Escape, sin Enter) equivalente a F-57.
2. **Inventario acotado:** `list_elements(role="Edit", max_depth=4)` en la banda superior — no
   `list_elements(role="SplitButton")` global ni `list_elements(role="Button")` del ribbon.
3. **Prohibido:** `find_element` por nombre de carpeta padre parcial (ej. segmento «Temp») para
   discover — navega fuera del lab; usar `mcp-value-filter` → `cancelled` + nota en flows.
4. Tras timing ≥3000 ms en find/list innecesario → `repo_hints_set(append=true)` con
   `nota: discover address band — Edit-first, no partial find`.

**Dónde:** `evaluacion-lab.md` § Modo B — fila **Barra direcciones / edición** (merge al implementar
con tabla breadcrumbs de propuesta `195900`).

## Contexto del turno

- Lab `escritorio-windows-2026-09-10`, `discover-F-12`, scope `subtree:F-12`.
- Evidence: Edit Dirección visible; `find_slow` 8967 ms; `list_split` 9535 ms; probe 393 ms;
  screenshot `_13.png`; encolado **F-57** pending, **F-58** / **F-59** cancelled (`skip_mcp_value`).
- `mcp-usage.jsonl`: `get_focused_element` OK **antes** del find lento (orden incorrecto).

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| find parcial «Temp» 9 s tras foco Edit | routing_tool | L3 | Sí (este archivo) |
| list SplitButton 9.5 s ventana entera | routing_tool | L3 | Sí (mismo bloque) |
| F-58/F-59 cancelled | ejecucion (filter OK) | — | No |
| Sin segmentos MenuItem en breadcrumbs | deteccion | L3 | Propuesta hermana `195900` / `195901` |
| find lento en hit | performance | L4 | No duplicar — mitigado por no invocar find; ver `195126` solo negativos |

## Texto propuesto

### Subárbol barra de direcciones — modo edición (discover B3–B4)

Después de B2 (re-invoke entry SplitButton breadcrumbs):

| Paso | Tool | Criterio |
|------|------|----------|
| 1 | `get_focused_element` | Role `Edit` en banda dirección |
| 2 | `read_element` / Value | Ruta legible; encolar verify Escape sin commit |
| 3 | Opcional | `list_elements(role="Edit", max_depth=4)` si foco ambiguo |
| 4 | Cierre | Escape; probe ventana lab |

**No** encolar acciones que naveguen a carpeta padre por botón de segmento ni Enter en Dirección
(lab sale de carpeta fija).

## Test de abstracción (L3)

Shell Win32 con combo/edit de ruta tras expandir breadcrumbs (Explorador, diálogos Abrir/Guardar).

## Verificación de duplicados

| Propuesta | Acción |
|-----------|--------|
| `20260910_195900_explorer-breadcrumb-flyout-verify-routing` | **Merge** — execute VERIFY + este discover |
| `20260910_195126_discover-subtree-flyout-menuitem-scan` | Distinto — flyout MenuItem contextual |
| `20260910_195330_discover-subtree-search-ribbon-splitbutton-routing` | Distinto — cinta búsqueda |
| `20260910_195126_find-element-name-search-negative-wall-clock` | Complemento código — misses; no sustituye routing |

## Esfuerzo observado

~18.5 s wall-clock evitable en discover subárbol F-12; F-57 encolado correctamente pero costo G6.

## Criterios de aceptación (mantenedor)

- [ ] Una sola tabla breadcrumbs en `evaluacion-lab` (execute + discover).
- [ ] Próximo `discover-F-12`: sin find parcial ni list SplitButton global; hints si slow.
- [ ] Texto sin nombre de carpeta lab ni «Temp».

## Beneficios futuros

Discover subárbol alinea con workaround ya probado (`get_focused_element`); menos latencia acumulada
en matriz Explorer sin nuevo código MCP.

# discover_flows — inventario post-expand SplitButton con include_offscreen

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 21:03:30 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | `awdui-mcp-automejora/references/evaluacion-lab.md` |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Versión MCP** | 0.4.0 |

## Resumen

**Problema:** En discover **subárbol** de entry ribbon tipo SplitButton (F-98 «Nuevo elemento»),
un `get_snapshot` con defaults **omite** `MenuItem` accionables (p. ej. «Carpeta») aunque el
flyout está abierto; el agente puede encolar 0 hijos o asumir inventario completo del pass anterior.

**Solución:** Tras B2 (`expand_element` / re-invoke del entry), inventario obligatorio:
`get_snapshot(max_depth=5, include_offscreen=true)` **o**
`list_elements(role="MenuItem", max_depth=4, include_offscreen=true)`; encolar hijos solo desde
ese listado; si hay nombres duplicados en UIA, preferir el nodo con bbox en client rect (screenshot
de verify). Tras encolar: `repo_hints_set` con `nota: ribbon flyout — snapshot include_offscreen`.

**Dónde:** `evaluacion-lab.md` § Modo B — tabla «Subárbol ribbon SplitButton»; merge al aplicar
con `20260910_195126_discover-subtree-flyout-menuitem-scan`.

## Contexto del turno

- Discover F-98: 13 flows F-163..F-175 encolados; `subtree_discovered=true`; validate 175 OK.
- Gap documentado en `improvements.jsonl` / `coverage.json` hasta fix código (propuesta
  `20260910_210330_menuitem-include-offscreen-post-expand-discovery`).

## Texto propuesto

### Subárbol entry SplitButton / menú desplegable (cinta)

Tras abrir el flyout (B2):

1. **Inventario:** `get_snapshot(max_depth=5, include_offscreen=true)` — no confiar en snapshot
   previo del padre con `include_offscreen=false`.
2. **Encolar:** solo `MenuItem` / `ListItem` presentes en ese inventario (whitelist por rol).
3. **Duplicados UIA:** si dos nodos mismo nombre (p. ej. dos «Carpeta»), elegir el asociado al
   flyout visible (bbox ∩ client rect) — no `find_element` global.
4. **Hints:** `repo_hints_set(append=true)` con `latencia:` si expand >3 s o si fue necesario
   `include_offscreen` manual antes del fix MCP.
5. **Teardown:** no depender solo de Escape con `focus_policy=minimal` — click en área lista o
   `focus_window` + Escape (ver friction F-98 execute).

## Test de abstracción (L3)

Cualquier cinta Win32 con SplitButton + popup MenuItem (Explorador, apps con ribbon clásico).

## Verificación de duplicados

| Propuesta | Acción |
|-----------|--------|
| `20260910_195126_discover-subtree-flyout-menuitem-scan` | **Merge** — añadir fila ribbon + include_offscreen |
| `20260910_195330_discover-subtree-search-ribbon-splitbutton-routing` | Complemento — cinta búsqueda |

## Esfuerzo observado

Workaround explícito en turno (`get_snapshot include_offscreen`); sin documentación unificada el
siguiente discover F-98 podría omitir F-163.

## Criterios de aceptación (mantenedor)

- [ ] Texto en evaluacion-lab sin IDs de flujo obligatorios (ejemplo genérico SplitButton).
- [ ] Cross-ref a propuesta código MenuItem default offscreen.
- [ ] Próximo discover F-98: inventario con offscreen documentado aunque MCP aún no auto-default.

## Beneficios futuros

Paridad discover flyout contextual (195126) y flyout ribbon; menos regresiones al ejecutar F-163..175.

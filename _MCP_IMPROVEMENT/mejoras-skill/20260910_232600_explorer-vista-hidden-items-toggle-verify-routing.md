# Explorer cinta Vista — toggle Elementos ocultos: verify sin find negativo

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 23:26:00 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | `awdui-mcp-automejora/references/evaluacion-lab.md`, merge al aplicar con `20260910_200930_explorer-vista-ribbon-vistas-verify-routing.md` |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Versión MCP** | v0.4.0 (lab run escritorio-windows-2026-09-10) |

## Resumen

**Problema:** En execute lab **F-151** (CheckBox **Elementos ocultos** en cinta Vista), el ACT
(`click_element` / invoke toggle on/off) fue **OK** (<1,1 s c/u), pero el VERIFY usó
`find_element(name="desktop.ini", …)` → **NOT FOUND ~30845 ms** (`find_neg` SLOW). Los
`success_criteria` del flujo piden «toggle verificado; probe sigue visible; estado restaurado» —
no exigen localizar un archivo oculto concreto en la carpeta lab (que puede no contener
`desktop.ini` aunque el toggle esté activo).

**Solución:** Documentar VERIFY para toggles **Mostrar/ocultar** en ribbon Explorer (y análogo
Win32 **CheckBox** / **Toggle** en barras de vista):

1. **ACT:** `invoke_element` o `click_element` en `CheckBox: Elementos ocultos` (Tab Vista
   previo si aplica).
2. **VERIFY (elegir uno, en orden):**
   - `get_control_state` / `read_element` / `TogglePattern` o `SelectionItem.is_selected` en
     el mismo CheckBox tras el click;
   - screenshot con estado checked/unchecked (`awdui_*` hito lab);
   - **solo si** el flujo o `discovery_signals` nombran un archivo oculto **y** la carpeta lab
     lo incluye: `list_elements(role=ListItem|DataItem, include_offscreen=true, max_depth=8)`
     acotado al **ItemsView**, filtrando por nombre parcial — **no** `find_element` global por
     nombre de archivo.
3. **Restaurar:** segundo toggle al estado inicial; verify probe rápido (`element_exists` en
   affordance estable del flujo, ej. SplitButton panel navegación) **< 3 s**.
4. **Prohibido:** `find_element` por `desktop.ini` / `$RECYCLE.BIN` / nombres genéricos de
   sistema cuando el criterio es solo «toggle verificado».

**Dónde:** Subsección «Explorer — cinta Vista, Mostrar u ocultar» en `evaluacion-lab.md`; al
aplicar, fusionar párrafo «sin find especulativo» con `200930` (botón Vistas) y `210615`
(SplitButton flyouts).

## Contexto del turno

- Lab `escritorio-windows-2026-09-10`, run `escritorio-windows-2026-09-10`.
- **F-151** `met` WARN; **F-152** `met` OK (`expand_element` Agregar columnas **828 ms**, sin coords).
- Evidence: `mcp-usage.jsonl` F-151 `find_neg` 30845 ms; `evidence.jsonl` verdict OK WARN;
  `flows.json` notas «find desktop.ini neg evitar».
- Blockers globales sin cambio: `teams_perfect` false (revalidación TE-02/06/08/10; cold
  `list_elements` Electron) — fuera de alcance de este turno Explorer.

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| find desktop.ini 30s NOT FOUND | performance + routing_tool | L3/L4 | Skill **este archivo**; código **consolidar** `20260910_195126_find-element-name-search-negative-wall-clock` (no duplicar) |
| Tab Vista invoke ~2s | performance | L3 | Backlog ribbon SLOW; no nuevo ítem |
| F-152 expand SplitButton OK | — | — | No — patrón ya cubierto por expand + teardown flyout (`210615`, `210330`) |

No es `ejecucion` pura en el miss de 30 s: aunque el agente no debía buscar `desktop.ini`, el
MCP aún permite quemar wall-clock en miss (backlog P1 `negative_fast`).

## Texto propuesto

### Explorer — toggle Elementos ocultos (cinta Vista)

1. Pre: cinta **Vista** activa (`invoke_element` TabItem Vista si el flujo lo requiere).
2. ACT: toggle on → verify estado del **mismo** CheckBox o screenshot; toggle off → verify
   restaurado.
3. No usar `find_element` por archivos ocultos salvo que `success_criteria` lo exija **y** un
   `list_elements` previo del ItemsView demuestre que el nombre existe en scope.
4. Tras WARN find neg evitable: `repo_hints_set(append=true)` — `nota: Vista Elementos ocultos
   — verify Toggle/screenshot; no find desktop.ini`.

## Test de abstracción (L3)

Cualquier shell Win32 con checkbox «elementos ocultos» / «extensiones de archivo» en ribbon o
menú Vista: verify por estado del control o listado acotado, no búsqueda negativa global.

## Verificación de duplicados

| Propuesta | Relación |
|-----------|----------|
| `20260910_200930_explorer-vista-ribbon-vistas-verify-routing` | Hermana — botón Vistas; **merge al aplicar** |
| `20260910_195126_find-element-name-search-negative-wall-clock` | Complemento código — F-151 añade evidencia ~30 s |
| `20260910_210615_explorer-vista-splitbutton-flyout-teardown` | Hermana — flyouts Ordenar/Agrupar; F-152 OK sin gap |

## Esfuerzo observado

~31 s evitables en un solo VERIFY de F-151; flujo igual `met` por screenshot + restore probe
348 ms.

## Criterio de aceptación

- [ ] Texto genérico Explorer / ribbon CheckBox toggle (no depender de carpeta lab vacía).
- [ ] Enlaza a backlog find fast-fail sin reimplementar.
- [ ] Replay F-151: sin `find_element` desktop.ini; verify incremental < **3 s** tras toggle.

## Beneficios futuros

- Cierra G6 eficiencia en oleada Vista (F-151..F-158) sin esperar solo fix código P1.
- Reduce falsos WARN en matriz lab cuando el toggle funciona pero el verify fue especulativo.

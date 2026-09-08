# Teams harness: gate teams_perfect — scroll-merge latency + sidebar state

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-06 22:46:02 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | teams-mcp-harness |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** Tras turno 6, `teams_matrix` 21/21 **met** pero `teams_perfect` sigue
`false`. La skill gate `213301` no refleja el nuevo trade-off scroll-merge: TE-02
funcional (49 items, virtualización resuelta) pero **3398 ms** cold SLOW; TE-03
`invoke(menur1r)` **12 s** por sidebar scrolleado post-list. El mantenedor no tiene
checklist actualizado para distinguir «gap virtualizado cerrado» vs «perf + estado UI».

**Solución:** Ampliar sección «Gate teams_perfect» en `teams-mcp-harness/SKILL.md`:

1. Fila TE-02: cold < **2000 ms** **o** `realize_virtualized=false` + find puntual
   documentado; count 49 no es blocker si target findable.
2. Fila TE-02/03: tras `list_elements(TreeItem)` con scroll-merge, invoke chat activo
   < **2000 ms** (sidebar no mutado) — blocker si solo OCR/screenshot salva el paso.
3. Nota: virtualización sidebar **resuelta** en MCP v0.4.0+ — no exigir workaround
   `find_element` para offscreen si list los incluye.
4. Referencia slugs backlog: `treeitem-scroll-merge-restore`, `treeitem-scroll-merge-cold-budget`.

**Dónde:** `.cursor/skills/teams-mcp-harness/SKILL.md` § Gate teams_perfect;
`.cursor/skills/teams/element-map.md` alinear WARN cold >3s con criterio gate.

## Texto propuesto

### Gate `teams_perfect` — actualización turno 6 (scroll-merge)

| Dimensión | Umbral | Blocker si falla |
|-----------|--------|------------------|
| TE-02 discovery cold | < **2000 ms** p95 con realize completo | 3398 ms SLOW — backlog cold-budget |
| TE-02 virtualización | Target offscreen (`menur*`) en list **o** find < 2 s | **Cerrado** turno 6 (49 items) |
| TE-02 → TE-03 invoke chat activo | < **2000 ms** sin OCR-only verify | menur1r 12 s — backlog sidebar-restore |
| Verify post-act TreeItem | < **1500 ms** p95 | Resuelto P1 (~426–956 ms) |
| Scroll historial TE-08 | `method` programático | Resuelto ancestor walk |
| Workarounds obligatorios | Ninguno no documentado | OCR post-list para re-select chat |

**Prohibido** `teams_perfect: true` si TE-03 invoke del chat ya abierto requiere OCR
porque `list_elements` dejó el sidebar scrolleado.

## Contexto del turno

- Implementado `_collect_treeitem_findall` scroll-merge + `ensure_focus` en keyboard nudge.
- Live: 49 TreeItems, Reyes menur31, cache 0 ms, TE-03 nav OK, menur1r re-select 12 s FAIL.
- pytest 16 passed; `state.json` next: optimize cold + restore sidebar.

## Verificación de duplicados

| Propuesta | Relación |
|-----------|----------|
| 213301 teams-perfect-gate-checklist | **Ampliar** — no duplicar archivo; merge texto o reemplazar sección TE-02/03 |
| 223500 virtualized gap | Cerrado — gate debe dejar de penalizar count 16 vs 23 |
| test-closure-evaluation.md | Complementa evaluación honesta MCP |

## Test de abstracción (L3)

Plantilla gate harness con dimensión perf + estado UI post-observación — reusable
Notepad/Teams sin IDs en metodología genérica.

## Esfuerzo observado

Matriz 21/21 met vs evaluación honesta nivel 3 = NO por cold 3.4 s + invoke 12 s post-list.

## Criterio de aceptación

- [ ] `teams-mcp-harness/SKILL.md` actualizado con tabla turno 6.
- [ ] TE-02 ya no exige count total chats como blocker si realize completo.
- [ ] Fila invoke post-discovery documentada con umbral 2000 ms.
- [ ] Sin rutas `_MCP_IMPROVEMENT/` en skill (solo slugs temáticos).
- [ ] `element-map.md` WARN alineado con gate (cold SLOW ≠ virtualización abierta).

## Beneficios futuros

- Cierre honesto `teams_perfect` cuando código P1 restore + budget estén aplicados.
- Evita confusión 49 items OK vs cold SLOW blocker.
- Paridad metodológica calculator/notepad perfect gates post-fix funcional.

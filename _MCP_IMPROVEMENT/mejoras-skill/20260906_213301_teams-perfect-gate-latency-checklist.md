# Teams harness: checklist gate teams_perfect (latency + calidad MCP)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-06 21:33:01 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | teams-mcp-harness |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** `teams_matrix` puede estar 21/21 **met** mientras `teams_perfect` permanece
`false`. Tras fix P1 verify (~426 ms TE-05), el agente/mantenedor carece de checklist
explícito en la skill harness que distinga **harness met** vs **calidad MCP operativa**
(análogo a `211201_calculator-perfect-gate-checklist` y `test-closure-evaluation.md`).

**Solución:** Añadir sección «Gate teams_perfect» en `teams-mcp-harness/SKILL.md` con tabla
de umbrales y blockers conocidos; referenciar backlog `_MCP_IMPROVEMENT` por tema (sin rutas
en chat agente). Incluir criterio post-fix verify y pendientes P1/P2.

**Dónde:** `.cursor/skills/teams-mcp-harness/SKILL.md` § nuevo «Gate teams_perfect»;
enlace a `patterns/test-closure-evaluation.md`.

## Texto propuesto

### Gate `teams_perfect: true` (no confundir con 21/21 met)

| Dimensión | Umbral | Blocker conocido si falla |
|-----------|--------|----------------------------|
| Verify post-act TreeItem | `verify_ms` < **1500 ms** p95; `verify_method` ∈ WindowTitle.* / ChatContext.* | Resuelto P1 2026-09-06 (~426 ms) |
| Discovery / find | `find_element` / `list_elements` < **2000 ms** p95 en flujos TE-02/05/10 | Backlog `panel_scope` / view_scope (204701) |
| Scroll historial TE-08 | `scroll_element` con `method` programático (ScrollPattern o **keyboard.**) — no solo coords | Backlog keyboard-before-coords (213300) |
| Envío TE-07 | Solo Nicolás Awamori; prefijo `[AwdUI-MCP-TE]` | — |
| Workarounds | Ninguno obligatorio no documentado en skill/gaps | scroll coords-only, verify duplicado manual |

**Prohibido** declarar `teams_perfect: true` solo porque `teams_matrix.*.status === met`.
Actualizar `state.json` → `teams_perfect` solo tras revisar tabla + evaluación honesta MCP.

## Contexto del turno

- Fix P1 verify aplicado: `_run_treeitem_title_verify` HWND-only poll; TE-05 426 ms ✓.
- `find_element` residual 8–14 s SLOW; scroll message pane ScrollPattern N/A.
- pytest 13 passed; matriz 21/21 met; `teams_perfect` false.

## Verificación de duplicados

- **Paralelo** a `211201_calculator-perfect-gate-checklist` — producto Teams, no duplica.
- **Complementa** `test-closure-evaluation.md` con umbrales numéricos Teams.
- **No duplica** `203601` verify fallbacks — documenta gate tras fix código P1.

## Test de abstracción (L3)

Patrón gate checklist aplicable a futuros harness (`teams-mcp-harness` template) — tabla
dimensión/umbral/blocker sin IDs de app en texto genérico de metodología cierre.

## Esfuerzo observado

Ciclo declaró 21/21 met; evaluación honesta exige separar harness vs MCP listo; usuario
turno cita blockers find/list + scroll explícitamente.

## Criterio de aceptación

- [ ] Sección en `teams-mcp-harness/SKILL.md` con tabla gate y prohibición met-only.
- [ ] Referencia a evaluación honesta MCP (plantilla test-closure).
- [ ] Umbrales verify 1500 ms y discovery 2000 ms citados.
- [ ] Sin rutas `_MCP_IMPROVEMENT/` en texto skill (solo slugs temáticos opcionales).
- [ ] `state.json` `last_cycle.next` alineado: P1 find/list, P2 scroll, re-eval gate.

## Beneficios futuros

- Evita cierre prematuro «Teams perfecto» tras matriz met.
- Orienta ciclo MCP post-21/21 hacia blockers medibles.
- Paridad metodológica con Calculadora/Notepad perfect gates.

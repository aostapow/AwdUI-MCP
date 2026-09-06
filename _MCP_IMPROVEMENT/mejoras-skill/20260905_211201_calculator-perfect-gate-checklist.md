# Calculadora — checklist gate antes de calculator_perfect

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-05 21:12:00 |
| **Skill objetivo** | calculator-mcp-harness |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Impacto** | medio |
| **MCP versión** | v0.2.1 |

## Resumen

**Problema:** Tras `exhaustive_act_verify` en las 9 pantallas, el turno `calculator_perfect_gate_reassess`
marcó **todos** los `completion_criteria` como `met` pero `calculator_perfect` siguió `false`.
Bloqueadores reales documentados en `state.json`: (1) `spy_tree max_depth≥12` solo en **Standard**
(252 nodos) — **1/9 modos**; (2) links legales About sin UIA; (3) verify `equalButton` fallido
(routing MCP — ver propuesta código `211200`). La skill no separa «exhaustive por control» de
«gate de cierre» con evidencia estructurada repetible.

**Solución:** Añadir sección **«Gate calculator_perfect (bloqueante)»** en
`calculator-mcp-harness/SKILL.md` con checklist explícito **antes** de proponer
`calculator_perfect: true`:

1. **spy_tree por modo:** para cada `automation_id` NavView (9 modos), `spy_tree(max_depth=12)`
   anotar `{modo: {node_count, max_depth, ts}}` en `calculator_evidence` — no alcanza un solo
   Standard 252.
2. **Sentinel aritmético reuse:** `clear→3+4=equal` con `verify_automation_id=CalculatorResults`
   (no `verify_name_contains` solo en equalButton hasta fix MCP).
3. **Settings About legal:** `expand_element(AboutExpander, verify_children=[AboutEULA, …])` o
   documentar gap abierto — no marcar gate Settings `met` sin links o propuesta código aplicada.
4. **Matriz vs gate:** `calculator_matrix.*.exhaustive_act_verify=met` **no implica**
   `calculator_perfect=true`; requiere además §Gate completo.

**Dónde:** `.cursor/skills/calculator-mcp-harness/SKILL.md`, `.cursor/mcp-improvement-cycle/state.json`
(campo `calculator_perfect_gaps` ya existe — alinear wording).

## Texto propuesto

### Gate calculator_perfect (bloqueante — además de §A–D)

No declarar `calculator_perfect: true` hasta:

| # | Evidencia | Tool MCP | Criterio OK |
|---|-----------|----------|-------------|
| G1 | spy_tree ×9 modos | `spy_tree(max_depth=12)` tras nav a cada modo | `node_count>0`, anotado por modo en evidence |
| G2 | Sentinel reuse | `invoke_element` teclado + `verify_automation_id=CalculatorResults` | Display numérico correcto sin relaunch |
| G3 | About legal UIA | `expand_element` + `verify_children` o gap documentado | Links EULA/Privacy/Services en árbol o propuesta `211000` pendiente |
| G4 | Segundo turno | Repetir G2 en turno distinto | Mismo resultado sin coords manuales |

Anti-patrón: marcar `criteria_status[].status=met` global si solo falta G1–G3.

## Contexto del turno

- `exhaustive_act_verify` **done** Standard→Settings (todas las pantallas §C).
- Gate reassess: Standard 3+4=7 spy OK; equal verify falló; spy_tree **1/9**.
- `calculator_perfect_gaps` en state.json lista los 3 bloqueadores.
- Skills leídas: `awdui-mcp-objective`, `calculator-mcp-harness` (no `awdui-flow-exploration`).

## Verificación de duplicados

- **Complementa** harness §A–D (modos, paneles, exhaustive) — no duplica OBS→ACT→VERIFY por control.
- **Referencia** propuesta código `211000` (About legal) y `211200` (verify target).
- Sin sección gate explícita previa en skill (solo criterios dispersos en §C y state.json).

## Test de abstracción

Patrón «lab app con matriz de cobertura + gate de cierre» aplica a futuros productos bajo
`.cursor/skills/{producto}/` — L3 metodológico, no IDs AST.

## Criterio de aceptación

- [ ] Sección Gate en skill con tabla G1–G4 y anti-patrón criteria_status.
- [ ] `state.json` `last_cycle.next` alineado con G1 (spy_tree 8 modos restantes).
- [ ] Sin nombres de usuario del turno en texto genérico (solo Calculadora como lab).

## Beneficios futuros

- Evita declarar `objective_met` con `calculator_perfect` falso por checklist incompleto.
- Agente distingue «pantalla exhaustive met» vs «producto lab perfecto».
- Reduce re-trabajo de gate reassess sin spy_tree en Científica→Settings.

## Esfuerzo observado

- Turno gate: re-verificación 3+4=7 + spy_tree Standard — **~5 min** agentico.
- Faltan 8× spy_tree (~2–4 min c/u si list_elements SLOW 3.5s) — estimado **20–30 min** gate restante.

## Estado post-turno `calculator_perfect_spy_tree_gate_complete` (2026-09-05 21:20)

| Gate | Estado | Nota |
|------|--------|------|
| G1 spy_tree ×9 | **met** | 240–283 nodos/modo; Header verificado; screenshots por modo |
| G2 sentinel reuse | **met (workaround)** | Display vía `spy_inspect(CalculatorResults)`; equal `verify_name_contains` falla — ver `211200` |
| G3 About legal | **met (workaround)** | Inner chevron click → `AboutEULA`, `AboutControlServicesAgreement`, `AboutControlPrivacyStatement` UIA ✓ |
| G4 segundo turno | **met** | Reuse PID sin relaunch; gate repetible |

**Skill aún pendiente de aplicar:** sección Gate en `calculator-mcp-harness/SKILL.md` sigue siendo
necesaria para futuros ciclos / regresiones aunque el objetivo durable ya esté `true`.

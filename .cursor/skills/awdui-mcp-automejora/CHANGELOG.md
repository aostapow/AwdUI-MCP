# Changelog — awdui-mcp-automejora

## 2.7.0 — 2026-09-11

### Añadido
- Cola canónica por app: `scripts/app_backlog_lib.py`, `init_or_resume_app_backlog.py`, `render_app_backlog.py`
- Patrón operativo [references/patterns/app-backlog.md](references/patterns/app-backlog.md)
- `SKILL.md` §4.5 Cola por aplicación (comandos, ciclo de turno, anti-patrones)
- Tests `tests/test_app_backlog_lib.py`

### Corregido
- Orden de cola: `priority: 0` en hygiene (no confundir con falsy en `or 99`)

### Cambiado
- `evaluacion-lab.md` — inicio de corrida vía backlog; `flows.json` como espejo perfect gate
- `check_mcp_objective.py` — prioriza `backlog_hint_for_state` y pregunta por `progress.complete`
- `state.json`: campos `active_app_slug`, `backlog_ref`, `lab_apps.*.backlog_progress`

## 2.6.0 — 2026-09-11

### Añadido
- Manifest `matrices/detection_baseline.json` + `lab-apps/detection-baseline.schema.json`
- `scripts/detection_baseline_lib.py`, `scripts/merge_detection_baseline.py`
- Regeneración automática del baseline en `incremental_lab_coverage`
- Hint advisory de baseline en `fix_in_cycle_gate` (generic vs celda eficiente)
- Tests `tests/test_detection_baseline_lib.py`

### Cambiado
- `mcp-usage.template.jsonl` incluye `framework`
- `evaluacion-lab.md` — campos obligatorios timing/framework en usage

## 2.5.0 — 2026-09-11

### Añadido
- `detection/frameworks/` — `FrameworkProfile`, registry, políticas por familia (UWP spy, backend order, depth)
- Patrón `references/patterns/framework-profiles.md`
- Gate `audit_fix_regression_scope` — `abstraction=generic` + núcleo compartido exige `regression_frameworks` ≥2
- Tests `tests/test_framework_profiles.py`, `tests/test_fix_regression_gate.py`

### Cambiado
- `orchestrator`, `tree_depth`, ramas UWP/spy en `ui_automation` usan perfiles
- `fix-in-cycle.md` + `last_cycle.fix_gate` (framework, abstraction, regression)

## 2.4.0 — 2026-09-11

### Añadido
- Gate `scripts/fix_in_cycle_gate.py` — lab activo: bloquea auto-continue si `flow_id` tiene fricción estructural sin resolver
- Hook `stop` antepone **FIX_IN_CYCLE BLOQUEADO** vía `check_mcp_objective.py`
- `scripts/grandfather-fix-friction-debt.py` — marcar deuda histórica `legacy_debt` en `improvements.jsonl`
- Tests `tests/test_fix_in_cycle_gate.py`

### Cambiado
- `last_cycle`: campos `flow_id`, `friction_logged`, `fix_gate`
- `fix-in-cycle.md` § Gate automático; regla `awdui-mcp-objective-persistent.mdc`

## 2.3.0 — 2026-09-08

### Añadido
- Patrón `references/patterns/mcp-value-filter.md` — omitir flujos discover/execute sin cobertura MCP nueva (objeto, patrón, tool o contexto no probado)

### Cambiado
- `evaluacion-lab.md`: sección valor MCP; checklist append `flows.json`; gate `perfect` acepta `cancelled` por `skip_mcp_value`
- `SKILL.md` §1 y §5.2: discover/execute priorizan valor MCP, no volumen de flujos
- Reglas `awdui-mission.mdc`, `lab-evaluacion.mdc` alineadas

## 2.2.0 — 2026-09-08

### Añadido
- Patrón `references/patterns/fix-in-cycle.md` — detectar fricción → fix en servidor → re-VERIFY; 3 intentos; revert + `pending_manual`
- `state.json` → `pending_manual_fixes[]`; `runs/{run}/pending-fixes.jsonl`
- `improvements.jsonl`: kinds `fix_attempt`, `fix_applied`, `fix_reverted`; campos `attempt`, `timing_before_ms` / `timing_after_ms`
- `evidence.jsonl`: bloque opcional `fix_cycle`

### Cambiado
- Protocolo lab execute: fricción slow/fail dispara fix_in_cycle antes de cerrar turno
- Reglas `lab-evaluacion.mdc`, `awdui-mcp-objective-persistent.mdc` alineadas

## 2.1.0 — 2026-09-08

### Añadido
- Tool MCP `repo_hints_set` + parámetro `agent_hints` en `repo_capture`
- Patrón `references/patterns/object-repository.md` (memoria institucional)
- `repo-snapshot.json` por corrida lab (hook incremental)
- Gate G8: `repo-snapshot.json` en `validate_perfect_gate.py`
- `flows.json`: campos opcionales `repo_path`, `repo_hints_note`

### Cambiado
- Lab / AST / metodología: obligación de depositar aprendizaje en `agent_hints`
- Evaluacion-lab § repo; hook pregunta crítica si hubo fricción sin hints

## 2.0.4 — 2026-09-08

### Afinado (narración)
- `action-narration.md`: narrar ≠ pedir permiso; alcance de tools; un turno = una tool
- Regla, misión, routing AST y hook alineados; tools meta exentas documentadas

## 2.0.3 — 2026-09-08

### Añadido
- Regla `awdui-action-narration.mdc` — narrar en chat antes de cada acción GUI
- Patrón `references/patterns/action-narration.md` (plantillas OBS/ACT/VERIFY en castellano)
- Hook y protocolo §5.2 refuerzan «Voy a…» antes de cada tool MCP

## 2.0.2 — 2026-09-08

### Añadido
- `scripts/validate_perfect_gate.py` — gate G1–G7 medible (`--json`, `--apply`)
- Hook: auto-check perfect vs gate; hint de elegibilidad en lab activo

## 2.0.1 — 2026-09-08

### Corregido
- Tabla markdown §6 Lab (columna `Concepto | Detalle`)
- `sync_state_coverage`: indent 4 espacios; sync `flows_progress` desde `flows.json`
- `validate_flows`: avisos vs errores (seeds encolados con padre pending = aviso)
- Hook: validación flows en incremental + auto-check `last_cycle` en lab

### Añadido
- Sidecar `runs/{run}/coverage-sync.json`
- Regla `lab-evaluacion.mdc` ampliada (artefactos, validate, cobertura)

## 2.0.0 — 2026-09-08

### Añadido
- Árbol de decisión por turno (pausa / AST / lab / solo MCP)
- Protocolo abrir / durante / cerrar con schema `last_cycle`
- Lab: flujos en árbol `entry` → `action`, discover en dos fases, encolado batch
- Cobertura incremental (`mcp-usage.jsonl`, `improvements.jsonl`, `coverage.json`, `lab-summary.md`)
- Scripts: `build_mcp_capability_catalog.py`, `lab_coverage_report.py`, `lab_coverage_diff.py`, `validate_flows.py`
- Troubleshooting y tabla de artefactos en SKILL
- Gate `perfect` documentado en evaluacion-lab.md

### Cambiado
- Entrada lab: solo nombre de app (sin manifest obligatorio)
- `completion_criteria` en state.json: redacción genérica multi-framework
- `mcp-cycle-controller`: sin referencia a Calculadora fija
- Frontmatter skill: sin `manifest en lab-apps/`

### Notas
- Universo de tools: `lab-apps/mcp-capability-catalog.json` (rebuild si cambia el servidor)
- `lab_apps.*.coverage` en state.json: lo actualiza el hook incremental (evitar editar en paralelo)

## 1.x (histórico)

- Skills separadas por app (calculator, teams, notepad) → archivadas en `runs/archive/legacy-skills/`
- Skill única `awdui-mcp-automejora` absorbe metodología y ciclo MCP

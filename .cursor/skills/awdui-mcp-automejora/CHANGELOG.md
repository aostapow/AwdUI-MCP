# Changelog — awdui-mcp-automejora

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

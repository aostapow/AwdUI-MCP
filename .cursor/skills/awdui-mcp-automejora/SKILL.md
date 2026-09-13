---
name: awdui-mcp-automejora
description: >-
  Skill única del repo AwdUI MCP: automejora del servidor Windows, metodología UI,
  lab opcional (solo nombre de app), flujos en árbol, cobertura incremental.
  Leer siempre esta skill + state.json antes de actuar.
disable-model-invocation: false
version: 2.7.0
---

# AwdUI MCP — automejora continua

Mejorar el **servidor MCP** para automatización Windows programática y agentica.  
Las apps de laboratorio son **vehículos opcionales** elegidos por el usuario — no forman parte del contrato de la skill.

## Índice

| Documento | Cuándo |
|-----------|--------|
| [references/metodologia-ui.md](references/metodologia-ui.md) | Cualquier interacción UI (fases 0–6) |
| [references/evaluacion-lab.md](references/evaluacion-lab.md) | Solo con `active_lab` o pedido explícito de lab |
| [references/patterns/app-backlog.md](references/patterns/app-backlog.md) | **Cola única por app** — obligatorio con `active_lab` |
| [references/patterns/repo-first-lab.md](references/patterns/repo-first-lab.md) | **Repo antes de discover** — solo aprender si repo falla |
| [CHANGELOG.md](CHANGELOG.md) | Historial de versiones de esta skill |
| [references/patterns/control-catalog.md](references/patterns/control-catalog.md) | Rol UIA → tool |
| [references/patterns/active-window.md](references/patterns/active-window.md) | Modales, foco, ventana hija |
| [references/patterns/action-narration.md](references/patterns/action-narration.md) | **Narrar en chat antes de cada acción GUI** |
| [references/patterns/object-repository.md](references/patterns/object-repository.md) | **Repo SQLite + agent_hints — memoria entre sesiones** |
| [references/patterns/test-closure-evaluation.md](references/patterns/test-closure-evaluation.md) | Cierre honesto harness vs MCP |
| [references/patterns/fix-in-cycle.md](references/patterns/fix-in-cycle.md) | **Detectar → arreglar → validar → revertir (3 intentos)** |
| [references/patterns/mcp-value-filter.md](references/patterns/mcp-value-filter.md) | **Omitir flujos sin objeto/patrón/tool nuevo** |
| [references/object-map-template.md](references/object-map-template.md) | Mapa UIA de una corrida |
| `lab-apps/mcp-capability-catalog.json` | Universo tools + controles (build script) |
| `lab-apps/flows.template.json` | Árbol de flujos (entry → action) |
| `lab-apps/mcp-usage.template.jsonl` | Registro de uso por invocación |
| `lab-apps/improvements.template.jsonl` | Registro de mejoras MCP |
| `docs/MCP_TOOLS_REFERENCE.md` | Contrato de tools |
| [ast-activities-manager](../ast-activities-manager/SKILL.md) | Producto AST (**no** es lab) |

Patrones por framework: `references/patterns/` (winforms, uwp-navview, win32-menubar, …).

---

## 1. Objetivo y alcance

| Entregable válido | No es entregable |
|-------------------|------------------|
| Fix en `mcp-servers/awdui-server/` + pytest | Script batch sin observación |
| Tool o patrón genérico reutilizable | Hardcode por app en el servidor |
| Evidencia en `state.json` / `runs/` | «Funcionó una vez» sin timing ni verify |
| Cobertura MCP **nueva** por flujo | Ejecutar flujos redundantes solo para subir `met/total` |

**Filtro de valor:** en lab/automejora, omitir flujos que no exponen objeto, patrón o tool no probado → [mcp-value-filter.md](references/patterns/mcp-value-filter.md).

| Propuesta en `_MCP_IMPROVEMENT/` si hay fricción | Coords/OCR como único camino sin documentar gap |

**Jerarquía de interacción:** `automation_id` + patterns → tools por rol → ventana/modal → OCR → coords (último recurso).

---

## 2. Árbol de decisión (cada turno)

```
¿cycle_control.paused o PAUSED?
  → Sí: atender usuario; no auto-continuar ciclo MCP
  → No: leer state.json

¿Pedido explícito de producto AST?
  → ast-activities-manager + metodologia-ui (set_target_window al terminar)

¿active_lab o usuario pidió evaluar con {app}?
  → app-backlog.md + evaluacion-lab.md
  → ¿existe apps/{slug}/backlog.json? NO → init_or_resume_app_backlog.py
  → Siguiente ítem = backlog.next_item_id (NO improvisar sin actualizar backlog)
  → execute/discover ↔ cobertura incremental; progress.complete false → NO cerrar lab
  → No: foco completion_criteria + current_focus (sin lab)
```

No mezclar lab con AST en el mismo turno salvo pedido explícito.

---

## 3. Niveles de «listo»

| Nivel | Flag | Significado |
|-------|------|-------------|
| 1 | `mcp_infra_ready` | Servidor arranca; tools responden |
| 2 | `lab_apps.{app}.perfect` | Corrida lab con evidencia (opcional) |
| 3 | `mcp_quality_status: operational` | Sin workarounds obligatorios del agente |

Matriz `met` ≠ MCP perfecto → [test-closure-evaluation.md](references/patterns/test-closure-evaluation.md).

### `objective_met`

```text
true SOLO SI:
  mcp_infra_ready
  Y todos completion_criteria en met (criteria_status)
  Y mcp_quality_status == operational
  Y (active_lab null O lab_apps[active_lab].perfect == true)
```

---

## 4. `state.json` — memoria durable

Ruta: `.cursor/mcp-improvement-cycle/state.json` — **no** usar el chat como memoria.

| Campo | Uso |
|-------|-----|
| `current_focus` | Un solo foco técnico del turno |
| `completion_criteria` / `criteria_status` | Checklist MCP global |
| `active_lab` | `null` o **nombre** de app (texto libre) |
| `active_app_slug` | Slug estable (`calculadora`) — cola en `apps/{slug}/` |
| `backlog_ref` | Ruta a `apps/{slug}/backlog.json` |
| `active_run` | Id carpeta bajo `runs/` (evidencia del turno) |
| `lab_apps.{app}` | `backlog_progress`, `coverage`, `perfect`, `flows_progress` (legacy) |
| `blockers` | Impedimentos activos (MCP caído, autodetect fallido, …) |
| `last_cycle` | Evidencia del **último** turno (obligatorio actualizar) |
| `mcp_quality_status` | `partial` \| `operational` |
| `cycle_control.paused` | Pausa hooks auto-continue |
| `pending_manual_fixes` | Fixes que fallaron 3 intentos en ciclo — revisión manual |

Campos legacy (`calculator_perfect`, `teams_matrix`, …) = histórico; **no** son contrato.

---

## 4.5 Cola por aplicación (obligatorio con `active_lab`)

**Documentación operativa completa:** [references/patterns/app-backlog.md](references/patterns/app-backlog.md) — leer antes del primer turno lab.

| Pregunta | Respuesta |
|----------|-----------|
| ¿Qué es la cola? | `apps/{slug}/backlog.json` — única lista de trabajo para esa app |
| ¿Cuándo crearla? | **Siempre** al iniciar o reanudar lab con un nombre de app |
| ¿Cómo? | `python scripts/init_or_resume_app_backlog.py "{nombre}"` |
| ¿Siguiente paso? | `next_item_id` en JSON (o salida del script) — **no** improvisar sin `mark_item` |
| ¿Cuándo parar lab? | `progress.complete === true` **o** pausa usuario — **no** por `flows.json` 26/26 `met` |
| Vista humana | `backlog.md` generado — **no editar a mano** |

### Comandos (copiar tal cual)

```powershell
cd C:\mcps\AwdUI-MCP

# Reinicio total (borrar escenarios y corridas de esa app)
python scripts/reset_app_lab.py "Calculadora"
python scripts/init_or_resume_app_backlog.py "Calculadora"

# Iniciar o reanudar (primera vez con corrida existente)
python scripts/init_or_resume_app_backlog.py "Calculadora" `
  --import-flows .cursor/mcp-improvement-cycle/runs/calculadora-2026-09-11/flows.json `
  --run-id calculadora-2026-09-11

# Tras cada turno que toque ítems
python scripts/render_app_backlog.py calculadora
```

### Ciclo de turno (resumen — detalle en app-backlog.md)

1. Leer `state.json` + `apps/{slug}/backlog.json`.
2. Trabajar **un** ítem (`next_item_id`): narrar → una tool GUI → VERIFY.
3. `mark_item` (`done` / `blocked` / …) vía `app_backlog_lib` o script auxiliar.
4. Append `mcp-usage.jsonl` / `evidence.jsonl` en `runs/{active_run}/`.
5. `render_app_backlog.py` + actualizar `lab_apps.{app}.backlog_progress` en `state.json`.
6. Si `progress.complete` sigue `false` → **no** declarar lab terminado.

Discover: nuevos candidatos → `add_discovered_items()`; no usar solo `flows.json` como cola mental.

### `pending_manual_fixes[]`

Cada ítem tras revertir un fix en ciclo:

```json
{
  "id": "fix-20260908-F06-selectionitem",
  "ts": "ISO8601",
  "flow_id": "F-06",
  "gap": "invoke_element SelectionItem verify en InvokePattern",
  "attempts": 3,
  "files_attempted": ["mcp-servers/awdui-server/..."],
  "improvement_ref": "_MCP_IMPROVEMENT/mejoras-codigo/....md",
  "run_id": "calculadora-2026-09-07"
}
```

### `last_cycle` (cerrar cada turno)

```json
{
  "ts": "ISO8601",
  "mode": "mcp_only | lab_execute | lab_discover | fix_in_cycle",
  "flow_id": "F-06",
  "focus": "texto de current_focus",
  "observe": "qué se leyó (tools + resultado breve)",
  "act": "qué se hizo (fix, un paso de flujo, encolado N flujos)",
  "verify": "pytest / MCP live / coverage — resultado",
  "live_verify": "ok | partial | no probado",
  "timing_ms": 450,
  "friction_logged": false,
  "fix_gate": {
    "status": "ok",
    "outcome": "none | fix_applied | not_needed | pending_manual | waived_skill_only",
    "framework": "uwp",
    "abstraction": "framework | generic | skill_only",
    "regression_frameworks": ["uwp", "win32"],
    "files_touched": []
  },
  "next": "único siguiente paso concreto"
}
```

**Lab + fricción estructural:** `friction_logged: true` y `fix_gate.status: ok` solo tras `fix_in_cycle` o cierre explícito (`not_needed` skill-only en `improvements.jsonl`). El hook `stop` reinyecta **FIX_IN_CYCLE BLOQUEADO** si el `flow_id` del turno tiene `fix_in_cycle: not_attempted` sin resolución. Fuera de `active_lab`, las mejoras pueden quedar en `_MCP_IMPROVEMENT/` para revisión manual.

---

## 5. Protocolo de un turno

### 5.1 Al abrir

1. Leer esta skill + `state.json`.
2. Si `active_lab`: leer **`apps/{active_app_slug}/backlog.json`** (§4.5); si falta → `init_or_resume_app_backlog.py`. Luego `runs/{active_run}/` para evidencia (`mcp-usage.jsonl`, `lab-summary.md`).
3. Respetar `blockers` antes de trabajo nuevo.
4. Elegir **un** modo según §2.

### 5.2 Durante

**Narración (siempre con GUI):** antes de cada tool MCP sobre la app, bloque «Voy a» en el **mismo mensaje** encima de la tool — ver [action-narration.md](references/patterns/action-narration.md).

**Repositorio (memoria entre sesiones):** tras entender un control estable → `repo_capture` si falta + `repo_hints_set` si hubo lección (workaround, verify, precondición). Antes de `repo_find`/`repo_action` → `repo_hints`. Ver [object-repository.md](references/patterns/object-repository.md).

| Modo | Acción |
|------|--------|
| **Sin lab** | Un fix o verificación MCP; pytest si tocó servidor |
| **Lab execute** | Siguiente ítem backlog (`next_item_id`) **con valor MCP**; un paso OBS→ACT→VERIFY; `mark_item` + `render_app_backlog`; fricción → **fix_in_cycle**; append `mcp-usage.jsonl` |
| **Lab discover** | Un barrido UI; encolar candidatos **con valor MCP** (omitir redundantes — ver [mcp-value-filter.md](references/patterns/mcp-value-filter.md)) |

**Fricción detectada (obligatorio):** no cerrar el turno solo con workaround. Seguir [fix-in-cycle.md](references/patterns/fix-in-cycle.md): aplicar fix en servidor → pytest → reiniciar MCP si aplica → **re-validar el mismo VERIFY**; máx. **3 intentos**; si no resuelve → `git checkout` archivos tocados → `pending_manual_fixes` + `pending-fixes.jsonl` + propuesta `_MCP_IMPROVEMENT/`.

Latencia: &lt;500ms fast · 500–3000ms ok · ≥3000ms slow (dispara fix_in_cycle si estructural).

### 5.3 Al cerrar (obligatorio)

1. Actualizar `last_cycle` en `state.json`.
2. **Lab:** append `mcp-usage.jsonl`; **todo diff en `mcp-servers/`** → `improvements.jsonl`; hook regenera cobertura + diff.
3. **Código MCP:** pytest relevante; si tools cambiaron → `docs/MCP_TOOLS_REFERENCE.md` + `validate_tools_reference.py`.
4. Resolver o documentar blockers; no borrar blockers sin verify.
5. Si marcas `perfect` u `objective_met` → plantilla [test-closure-evaluation.md](references/patterns/test-closure-evaluation.md).

---

## 6. Lab (resumen — detalle en evaluacion-lab.md)

| Concepto | Detalle |
|----------|---------|
| Entrada | Solo nombre de app + flujos seed opcionales |
| Cola | `init_or_resume_app_backlog.py` → `apps/{slug}/backlog.json` (§4.5) |
| Autodetect | `discovered.yaml` — sin pedir framework/exe al usuario |
| Flujos | Ítems `category: flow` en backlog; árbol `parent_id`; discover → `add_discovered_items` |
| Turno | Un ítem backlog (execute) ↔ discover (encolar en backlog) |
| Cobertura | Incremental cada turno; `backlog_progress` + `coverage` (hook) |
| Sidecar | `runs/{run}/coverage-sync.json` — espejo para merge manual si hace falta |

**Antes de guardar `flows.json`:** checklist en evaluacion-lab.md § «Checklist antes de append» + `python scripts/validate_flows.py`.

**Mejoras MCP en corrida lab:** todo diff en `mcp-servers/awdui-server/` → línea en `improvements.jsonl`.

Comandos:

```powershell
python scripts/validate_perfect_gate.py
python scripts/build_mcp_capability_catalog.py
python scripts/lab_coverage_report.py
python scripts/lab_coverage_diff.py
python scripts/validate_flows.py
python scripts/validate_perfect_gate.py
python scripts/init_or_resume_app_backlog.py "{app}"
python scripts/render_app_backlog.py {slug}
python .cursor/hooks/check_mcp_objective.py --mode status
```

### Gate `lab_apps.{app}.perfect`

Ver evaluacion-lab.md (G1–G7 vía `validate_perfect_gate.py`; cierre honesto MCP obligatorio).

---

## 7. Criterios MCP (`completion_criteria`)

1. Infra UIA y patterns por rol  
2. `tool_validation_matrix` con evidencia por tool  
3. Detección en ≥2 frameworks (evidencia en state, no apps fijas en skill)  
4. Eficiencia: sin slow ≥3s sin blocker documentado  
5. Evaluación crítica de tools frágiles (`critical_notes` en matriz)

> **Nota:** `state.json` puede contener criterios redactados con apps históricas; interpretar como evidencia multi-framework, no como obligación de esas apps.

---

## 8. Artefactos por corrida (`runs/{active_run}/`)

| Archivo | Rol | Actualización |
|---------|-----|----------------|
| `discovered.yaml` | Autodetect | Una vez al inicio |
| `flows.json` | Espejo/evidencia perfect gate (cola real = backlog) | Opcional sync; no decidir parada por `met/total` solo |
| `mcp-usage.jsonl` | Uso MCP | Append cada invocación |
| `improvements.jsonl` | Mejoras MCP | Append cada fix |
| `coverage.json` | Métricas vs universo | Regenerado cada turno |
| `lab-summary.md` | Resumen humano | Regenerado cada turno |
| `evidence.jsonl` | OBS/ACT/VERIFY (+ `fix_cycle` si hubo arreglo) | Append cada paso |
| `pending-fixes.jsonl` | Fixes revertidos tras 3 intentos | Append al revertir |
| `element-map.md` | Mapa UIA | Durante discovery |
| `repo-snapshot.json` | Objetos repo + agent_hints | Regenerado cada turno (hook) |
| `coverage-diff.md` | Δ vs corrida anterior misma app | Tras incremental (si hay previa) |

> **`lab_apps.*.coverage` en state.json:** lo escribe el hook incremental; el agente no lo edita manualmente salvo corrección puntual.

---

## 9. Troubleshooting

| Síntoma | Acción |
|---------|--------|
| MCP en Error / `Connection closed` | `scripts/restart-awdui-mcp.ps1`; `check_version`; blocker hasta ok |
| `find_element` slow o stale | Diagnóstico UIA; fix servidor; no reintentar ciego |
| Autodetect falla | `list_windows`; override en `lab-apps/overrides/`; blocker |
| Menú cerrado antes de discover hijos | Re-ejecutar `entry` padre un paso |
| Hook empuja lab pero usuario pidió otra cosa | Atender usuario; no declarar `objective_met` |
| `coverage` desactualizado | Verificar append `mcp-usage.jsonl`; `lab_coverage_report.py` |

---

## 10. Pausa, hooks y controlador

```powershell
& scripts/pause-mcp-cycle.ps1 -Reason "..."
& scripts/resume-mcp-cycle.ps1
```

- **Hooks** (`sessionStart` / `stop`): inyectan foco si `objective_met` false y no pausado.
- **Controlador** (background): actualiza `last_cycle`, `cycle.log` — ver `.cursor/agents/mcp-cycle-controller.md`.

---

## 11. Anti-patrones

- Apps fijas en skill o servidor MCP  
- Lab sin `active_lab` ni pedido explícito  
- Un turno discover que ejecuta flujos recién encolados  
- Un turno execute con batch de pasos sin VERIFY  
- Acción GUI sin narrar «Voy a» previa en chat (salvo `sin narrar` del usuario)
- Hijos de menú sin `entry` padre `met`  
- `objective_met` / `perfect` con workarounds obligatorios  
- Omitir `mcp-usage.jsonl` o `last_cycle`  
- Cerrar con «N/N met» sin evaluación honesta MCP  
- Fricción slow/fail documentada sin **fix_in_cycle** (3 intentos + revert si falla)  
- Ejecutar flujos lab **sin cobertura MCP nueva** solo para inflar `met/total`  
- Cerrar lab con `flows.json` todo `met` sin `backlog.progress.complete`  
- Saltar `init_or_resume_app_backlog` o editar `backlog.md` a mano  

---

## 12. Comandos de verificación

```powershell
python .cursor/hooks/check_mcp_objective.py --mode status
& "$env:USERPROFILE\.awdui-mcp\.venv\Scripts\python.exe" -m pytest tests/ -q --tb=short
python scripts/validate_tools_reference.py
python scripts/validate_flows.py
```

---

## Otras skills del repo

| Skill | Rol |
|-------|-----|
| **awdui-mcp-automejora** | Esta — MCP + lab genérico |
| ast-activities-manager | Producto AST |
| awdui-mcp-improvement-advisor | Retrospectiva (background) |

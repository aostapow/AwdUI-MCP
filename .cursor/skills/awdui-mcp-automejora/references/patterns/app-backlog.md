# Cola canónica por aplicación (`apps/{slug}/backlog.json`)

**Regla:** con `active_lab` seteado, esta cola es la **única lista de trabajo** del agente para esa app.  
No cerrar lab ni decir «prueba terminada» mientras `progress.complete` sea `false`, salvo `pause-mcp-cycle` o pedido explícito del usuario.

`flows.json` por corrida queda como **espejo/evidencia** (perfect gate); **no** sustituye al backlog.

**Repo-first:** por cada ítem `pending`, intentar `repo_find` / `repo_action` antes de discover masivo — ver [repo-first-lab.md](repo-first-lab.md).

---

## Rutas

| Archivo | Rol |
|---------|-----|
| `.cursor/mcp-improvement-cycle/apps/{slug}/backlog.json` | **Canónico** — leer/escribir con `app_backlog_lib` |
| `.cursor/mcp-improvement-cycle/apps/{slug}/backlog.md` | **Generado** — solo lectura humana |
| `.cursor/mcp-improvement-cycle/apps/{slug}/manifest.json` | `active_run`, framework |
| `state.json` → `active_app_slug`, `backlog_ref`, `active_run` | Punteros del ciclo |
| `runs/{active_run}/` | Evidencia: `mcp-usage.jsonl`, `evidence.jsonl`, `discovered.yaml` |

`slug` = nombre de app normalizado (`Calculadora` → `calculadora`).

---

## Reiniciar una app desde cero (borrar escenarios)

Cuando el usuario pide **limpiar** y volver a empezar (sin mezclar flows/backlog viejos):

```powershell
cd C:\mcps\AwdUI-MCP
python scripts/reset_app_lab.py "Calculadora"
python scripts/init_or_resume_app_backlog.py "Calculadora"
```

| Qué hace `reset_app_lab` | Qué **no** borra |
|--------------------------|------------------|
| `apps/{slug}/` (backlog + manifest) | Otras apps en `lab_apps` |
| `runs/{slug}-*` (flows, evidence, coverage) | `matrices/` globales, Teams/Notepad |
| Entrada `lab_apps.{App}`; `calculator_matrix` / `calculator_evidence`; CAL-* en `ast_skill_consultation` | `objective_met` global; otras apps en `lab_apps` |

**No** usar `--import-flows` tras un reset salvo que quieras re-importar a propósito. La cola nueva queda solo con ítems **hygiene** (Fase 0).

---

## Iniciar aprendizaje de una app (obligatorio)

Cuando el usuario pide evaluar / iniciar ciclo con **{nombre de app}**:

```powershell
cd C:\mcps\AwdUI-MCP
python scripts/init_or_resume_app_backlog.py "{nombre}"
```

Primera vez (ej. importar flujos de una corrida vieja):

```powershell
python scripts/init_or_resume_app_backlog.py "Calculadora" `
  --import-flows .cursor/mcp-improvement-cycle/runs/calculadora-2026-09-11/flows.json `
  --run-id calculadora-2026-09-11
```

| Resultado | Acción del agente |
|-----------|-------------------|
| **CREATED** | Seguir con Fase 0 si ítems `hygiene` pending |
| **RESUMED** | Leer `next_item` del script o `backlog.json` → `next_item_id` |

Luego: `resume-mcp-cycle.ps1` si estaba pausado.

---

## Ítems (`items[]`)

| Campo | Valores |
|-------|---------|
| `id` | `W-H01`, `W-F-01`, … |
| `category` | `hygiene` \| `flow` \| `tool` \| `gate` |
| `status` | `pending` \| `in_progress` \| `done` \| `blocked` \| `na` \| `cancelled` |
| `title`, `success_criteria`, `notes` | Funcional + verify |
| `ref` | Ej. `F-01` (flujo), `phase0`, nombre tool |
| `parent_id` | Otro `id` backlog (padre debe estar `done` para ejecutar hijo) |
| `priority` | Menor = antes |
| `evidence[]` | Rutas o anchors a `evidence.jsonl` |

### Completitud

```json
"progress": {
  "complete": true   // solo si no quedan pending | in_progress | blocked
}
```

---

## Ciclo de un turno (no desviarse)

```
1. Leer state.json + apps/{slug}/backlog.json
2. Elegir ítem = next_item_id (o primer pending elegible)
3. Narrar «Voy a…» → una tool MCP GUI → resultado
4. mark_item(id, "done"|"blocked"|…) en código o al cerrar turno
5. append mcp-usage.jsonl + evidence.jsonl (runs/{active_run}/)
6. python scripts/render_app_backlog.py {slug}
7. Actualizar last_cycle + lab_apps.{app}.backlog_progress en state
8. Si progress.complete aún false → NO declarar cierre; hook stop continuará
```

### `discover_flows`

- **No** usar `list_elements` amplio por defecto si hay alternativa (`discover_control_interaction`).
- Nuevas affordances → `add_discovered_items()` en `app_backlog_lib` (status `pending`, `source: discovered`).
- Regenerar `backlog.md`; opcional sincronizar `flows.json` en corrida (fase M2).

### `execute_flow`

- Un ítem backlog = un paso OBS→ACT→VERIFY (o un sub-paso si el ítem es grande — preferir ítems atómicos al discover).

---

## API Python (`scripts/app_backlog_lib.py`)

| Función | Uso |
|---------|-----|
| `init_or_resume(app_name, …)` | Crear o reanudar + patch `state.json` |
| `load_backlog(slug)` / `save_backlog(slug, data)` | IO |
| `next_pending_item(backlog)` | Siguiente trabajo |
| `mark_item(backlog, id, status, notes=, evidence=)` | Cerrar paso |
| `add_discovered_items(backlog, candidates, run_id=)` | Tras discover |
| `render_backlog_markdown` / `write_backlog_md` | Vista MD |
| `backlog_hint_for_state(state)` | Texto para hook |

---

## Qué NO es el backlog

| Artefacto | Rol real |
|-----------|----------|
| `tool_validation_matrix.json` | Global MCP tools — actualizar al cerrar ítems `category: tool` |
| `criteria_status` en `state.json` | Objetivo MCP **global** (no por app) |
| `coverage.json` / `lab-summary.md` | Informe de la corrida actual |
| `flows.json` met/total | Legacy/espejo — **no** decidir parada por «26/26 met» copiados |

---

## Anti-patrones

- Editar `backlog.md` a mano.
- Dar por cerrado el lab porque `flows.json` está todo `met` sin mirar `backlog.progress.complete`.
- Saltar `init_or_resume_app_backlog` al cambiar de app.
- Ignorar `next_item_id` y improvisar `current_focus` sin sincronizar backlog.

---

## Referencias

- Skill: `SKILL.md` § Cola por aplicación
- Lab genérico: `evaluacion-lab.md` (Fase 0, discover, execute — siempre vía backlog)
- Hook: `check_mcp_objective.py` prioriza `backlog_hint_for_state`

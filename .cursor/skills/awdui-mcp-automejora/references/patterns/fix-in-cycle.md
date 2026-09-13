# Arreglo en ciclo — detectar, aplicar, validar, revertir

Parte de [awdui-mcp-automejora](../../SKILL.md). Aplica en **cualquier turno** del ciclo MCP (lab o sin lab) cuando se detecta fricción estructural, no solo workaround de skill.

## Disparo obligatorio

Entrar en sub-modo `fix_in_cycle` cuando en OBS, ACT o VERIFY aparezca:

| Señal | Ejemplo |
|-------|---------|
| Timing **slow** (≥3000 ms) estructural | `find_element` 8 s, `list_elements` cold 3.5 s |
| Verify **fail** con act OK | `invoke_element` SelectionItem 10 s fail; display correcto |
| Tool devuelve NOT FOUND / stale repetido | `HistoryFlyout`, `MemoryButton` stale |
| Gap tipificado en catálogo MCP | verify pattern incorrecto, scope leak, cache stale |

**No disparar** para quirks puros de producto documentables solo en `repo_hints` (precondición «cerrar historial antes de M+») **salvo** que el MCP deba absorberlo genéricamente.

## Flujo integrado en `execute_flow`

El turno lab **no termina** solo con workaround. Tras detectar fricción:

```
OBS → ACT → VERIFY (falla o slow)
  → fix_in_cycle (hasta 3 intentos)
  → VERIFY de nuevo (mismo paso / mismo flow_id)
  → evidence.jsonl + improvements.jsonl
  → continuar flujo o marcar partial
```

Un turno puede incluir **fix + re-verify**; sigue siendo un solo `flow_id` en `evidence.jsonl` con campo `fix_cycle`.

## Sub-modo `fix_in_cycle` (máx. 3 intentos)

### Antes del intento 1

1. Registrar línea `kind: friction` en `improvements.jsonl` (gap, `flow_id`, `timing_ms`, `proposal`).
2. **Snapshot código:** `git diff --name-only mcp-servers/` (lista de archivos a revertir si falla).
3. Opcional: `git stash push -m "fix-cycle-{flow_id}-attempt-N" -- mcp-servers/` si ya hay WIP mezclado.

### Cada intento (1..3)

| Paso | Acción |
|------|--------|
| 1 | Implementar **fix mínimo** en `mcp-servers/awdui-server/` (agnóstico de app) o test que fije regresión |
| 2 | `pytest` del módulo tocado (obligatorio si hubo diff en servidor) |
| 3 | Si tocó servidor MCP → `scripts/restart-awdui-mcp.ps1` → `check_version` |
| 4 | **Re-ejecutar VERIFY** del paso que falló (mismos parámetros; narrar «Voy a revalidar…») |
| 5 | Criterio de éxito: verify OK **y** timing &lt;3000 ms **o** mejora medible ≥50 % vs baseline documentado |
| 6 | Append `improvements.jsonl` con `kind: fix_attempt`, `attempt: N`, `outcome: ok\|fail`, `timing_before_ms`, `timing_after_ms` |

### Si un intento tiene éxito

1. `kind: fix_applied` en `improvements.jsonl` (`files`, `tests`, `benefit`, `evidence`).
2. Actualizar `docs/MCP_TOOLS_REFERENCE.md` si cambió contrato de tool.
3. `python scripts/validate_tools_reference.py` si aplica.
4. Continuar el flujo (`status: met` si `success_criteria` cumplido).
5. **No** revertir.

### Si tras 3 intentos sigue fallando

1. **Revertir código** al estado pre-fix:
   ```powershell
   git checkout -- mcp-servers/awdui-server/
   git checkout -- tests/
   git checkout -- docs/MCP_TOOLS_REFERENCE.md
   ```
   (solo archivos listados en el snapshot del paso 1; no tocar artefactos de lab.)
2. Reiniciar MCP si se había reiniciado para el fix.
3. Append `improvements.jsonl`:
   ```json
   {
     "kind": "fix_reverted",
     "status": "pending_manual",
     "flow_id": "F-06",
     "attempts": 3,
     "summary": "...",
     "files_attempted": ["..."],
     "revert_command": "git checkout -- ...",
     "manual_review": "_MCP_IMPROVEMENT/mejoras-codigo/..."
   }
   ```
4. Append línea en `runs/{active_run}/pending-fixes.jsonl` (mismo payload).
5. Añadir entrada en `state.json` → `pending_manual_fixes[]` (ver SKILL §4).
6. Propuesta en `_MCP_IMPROVEMENT/mejoras-codigo/` con `Estado: propuesta` si no existe.
7. Continuar el flujo con **workaround documentado** en `repo_hints_set` / notas del flujo; `status: partial` o `met` con nota de workaround **solo si** el criterio funcional se cumple sin el fix MCP.

## Sin lab activo

Mismo protocolo al detectar fricción en trabajo MCP directo:

1. friction → fix_in_cycle (3 intentos) → pytest + MCP live verify.
2. Fallo → revert + `pending_manual_fixes` en `state.json`.

## Campos `evidence.jsonl`

```json
{
  "mode": "execute_flow",
  "flow_id": "F-06",
  "fix_cycle": {
    "triggered": true,
    "attempts": 2,
    "outcome": "applied",
    "timing_before_ms": 10963,
    "timing_after_ms": 520
  },
  "outcome": "met"
}
```

Si `outcome: reverted`: `fix_cycle.outcome: "pending_manual"`.

## Gate automático (lab activo)

Mientras `active_lab` está seteado y el ciclo **no** está pausado:

1. Cada turno lab debe incluir `last_cycle.flow_id` y, si hubo fricción MCP, `friction_logged: true`.
2. No cerrar el turno con `fix_gate.status: ok` hasta:
   - `fix_applied` / `fix_reverted` (→ `pending_manual`) en `improvements.jsonl` para ese `flow_id`, **o**
   - `fix_in_cycle: not_needed` en la línea de fricción (solo skill/repo_hints; marcar `skill_only: true` si aplica).
3. El hook `stop` (`check_mcp_objective.py`) antepone **FIX_IN_CYCLE BLOQUEADO** al `followup_message` si queda fricción abierta para el `flow_id` del último turno.
4. Auditoría manual: `python scripts/fix_in_cycle_gate.py --state .cursor/mcp-improvement-cycle/state.json`

Deuda histórica (corridas anteriores al gate): actualizar líneas a `fix_in_cycle: legacy_debt` o resolver con fix real antes de reanudar el mismo `flow_id`.

Fuera de lab (`active_lab: null`): no aplica el gate; el advisor y `_MCP_IMPROVEMENT/` siguen siendo revisión manual.

## Clasificación framework vs genérico

Antes del intento 1, leer [framework-profiles.md](framework-profiles.md) y fijar en `last_cycle.fix_gate`:

| Campo | Valores |
|-------|---------|
| `framework` | Familia del turno (`detect_framework`) |
| `abstraction` | `framework` \| `generic` \| `skill_only` |
| `regression_frameworks` | Obligatorio si `generic` y tocas núcleo UIA/orchestrator (≥2) |
| `files_touched` | Lista de paths bajo `mcp-servers/` del diff |

En `improvements.jsonl` (`fix_applied` / `friction`), repetir `framework` y `abstraction`.

## Anti-patrones

- Documentar fricción en `improvements.jsonl` y **seguir** sin intentar fix en servidor.
- Dejar código roto tras 3 fallos (obligatorio revert).
- Más de 3 intentos en el mismo gap en un turno (escalar a `pending_manual`).
- Fix específico de Calculadora/AST en `mcp-servers/` (ver `awdui-app-agnostic.mdc`).
- Omitir pytest tras cambio en servidor.

## Comandos rápidos

```powershell
& "$env:USERPROFILE\.awdui-mcp\.venv\Scripts\python.exe" -m pytest tests/ -q --tb=short
& scripts/restart-awdui-mcp.ps1
git diff --name-only mcp-servers/ awdui-server tests/
git checkout -- mcp-servers/awdui-server/path/to/file.py
```

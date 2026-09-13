# Repo-first en lab (no redescubrir objetos conocidos)

Con `active_lab`, **antes** de `discover_control_interaction`, `list_elements` amplio o `spy_tree` profundo:

## Protocolo por ítem backlog

1. `repo_list` o `repo-snapshot.json` de la corrida → ¿hay `repo_path` para el paso?
2. **Intento rápido:** `repo_find` + `repo_action` o `invoke_element` por `automation_id` estable + VERIFY.
3. **OK** sin fricción nueva → `mark_item` `done`/`na`, nota `skip_mcp_value: repo_hit`. **No** barrido de árbol.
4. **FAIL** (not found, verify, slow ≥3s estructural) → discover acotado + `repo_capture` / `repo_hints_set` + fix_in_cycle si aplica.

## Estabilidad de propiedades

Tras éxitos repetidos, consultar `repo_identification_stats(repo_path=...)`:

- Props **stable** → candidatas a identificación rápida (p. ej. `automation_id`).
- Props **volatile** → no usar como mandatory (bbox, `name` que cambia con modo UWP).

Historial: tabla `property_observations` en `~/.awdui-mcp/repository.db` (solo paths exitosos).

## Relación con mcp-value-filter

- **Omitir** flujo si mismo `repo_path` + verify OK y `success_count` alto sin novedad MCP.
- **Ejecutar** si `repo_find` falla, contexto nuevo (modal/modo), o stats muestran propiedad antes stable ahora volatile.

## Referencias

- [object-repository.md](object-repository.md)
- [app-backlog.md](app-backlog.md)
- `scripts/analyze_repo_property_stability.py` (informe offline)

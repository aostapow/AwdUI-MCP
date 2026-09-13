# Corridas de evaluación lab (temporal)

Artefactos **por corrida**, no parte de skills.

```
runs/{run_id}/
  discovered.yaml
  flows.json
  mcp-usage.jsonl      # cada tool/rol/pattern usado
  improvements.jsonl   # cada mejora MCP en la corrida
  pending-fixes.jsonl  # fixes revertidos tras 3 intentos (revisión manual)
  coverage.json        # regenerado cada turno (acumulado desde mcp-usage)
  lab-summary.md       # regenerado cada turno
  coverage-diff.json   # opcional — Δ vs corrida anterior misma app
  coverage-diff.md
  evidence.jsonl
  element-map.md
  safety.yaml
  screenshots/
```

## Flujos

- Seeds iniciales: mensaje del usuario o `lab-apps/seeds/{slug}.json`
- Plantilla: `lab-apps/flows.template.json`
- Protocolo alternado: `execute_flow` ↔ `discover_flows` — ver `evaluacion-lab.md`

Crear al activar `active_lab` en `state.json`. Archivar o borrar al cerrar la corrida.

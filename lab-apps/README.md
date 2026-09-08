# Lab apps — autodetección + catálogo de flujos

El usuario da el **nombre de la aplicación** y, opcionalmente, **pocos flujos funcionales** conocidos.  
Framework, ventana y launch → autodetect. El catálogo de flujos **crece** en cada corrida.

## Corrida nueva

1. Usuario: «evaluá el MCP con {nombre}» (+ flujos opcionales: «suma 2+2», «guardar archivo»)  
2. `state.json`: `active_lab: "{nombre}"`, `active_run: "{slug}-YYYY-MM-DD"`  
3. Evidencia: `.cursor/mcp-improvement-cycle/runs/{active_run}/`  
   - `discovered.yaml` — autodetección  
   - `flows.json` — seeds + flujos descubiertos (vivo)  
   - `element-map.md`, `evidence.jsonl`

## Catálogo y cobertura

- Universo MCP: `python scripts/build_mcp_capability_catalog.py` → `mcp-capability-catalog.json`
- Informe corrida: `python scripts/lab_coverage_report.py`
- Diff vs corrida anterior: `python scripts/lab_coverage_diff.py`
- Validar flujos: `python scripts/validate_flows.py`

- Plantilla: [flows.template.json](flows.template.json)  
- Seeds opcionales: [seeds/](seeds/)  
- Alternancia por turno: `execute_flow` (1 paso) ↔ `discover_flows` (1 escaneo; **encolar todos** los flujos nuevos visibles — 1 o 10+)

## `examples/`

Manifests históricos (calculator, notepad, teams). No obligatorios.

## `overrides/` (opcional)

Pistas si autodetección falla — ver [manifest.template.yaml](manifest.template.yaml).

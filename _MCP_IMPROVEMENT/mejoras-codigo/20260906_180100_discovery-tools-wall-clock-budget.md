# discover_target / spy_walk_visible: presupuesto wall-clock y fast mode

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-06 18:01:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | detection/discovery/runner.py, tools/spy_walk.py, tools/discovery.py |
| **Tool afectada** | discover_target_tool, spy_walk_visible_tool |
| **Tipo de gap** | performance |
| **Nivel** | L4 |
| **Versión MCP** | 0.2.1 |

## Resumen

**Problema:** `discover_target_tool(max_steps=2)` y `spy_walk_visible_tool(batch_size=2)` provocan
**MCP Request timed out (30s)** en Calculadora, incluso tras restart. Bloquean auditoría wave_9
y suman a los 8 fail de `objective_met`.

**Solución:** (1) Parámetro `max_wall_ms` (default 12000) en discover runner — abortar loop y
retornar partial plan + steps ejecutados. (2) `spy_walk_visible`: `pause_ms=0` default en modo
audit; cap `batch_size` efectivo cuando `max_wall_ms` seteado; skip `highlight_element_dict`
si `fast=true`. (3) Respuesta JSON siempre antes del timeout MCP con `timed_out: true`.

**Dónde:** `runner.py`, `spy_walk.py`, tool schemas; tests
`tests/test_discovery_wall_clock.py`.

## Contexto del turno

- Matriz: discover_target_tool fail 30s; spy_walk_visible_tool fail 30s post-restart.
- Notepad NP-12/13 met — sin fricción en estas tools este turno.
- `build_detection_context` slow pero completa (3500ms) — contraste: discovery no retorna.

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| discover_target 30s timeout | performance | L4 | Sí |
| spy_walk highlight 800ms × batch | performance | L4 | Sí (mismo archivo) |
| NP-12 spy_tree raw 6222ms | performance | L3 | Skill documenta; aceptable con verify |

`discover_target` ejecuta hasta 15 steps con `wait_for_change(2s)` — trivialmente >30s.
`spy_walk` con `pause_ms=800` y list_elements fallback lento excede presupuesto agentico.

## Cambio propuesto

```python
# runner.discover_target
def discover_target(..., max_wall_ms: int = 12000, max_steps: int = 15):
    deadline = time.monotonic() + max_wall_ms / 1000
    for step in range(max_steps):
        if time.monotonic() >= deadline:
            return {"success": False, "timed_out": True, "steps_done": step, ...}
        ...
```

```python
# spy_walk_visible
def spy_walk_visible(..., pause_ms: int = 0, fast: bool = False, max_wall_ms: int = 10000):
    if fast:
        pause_ms = 0
    # skip highlight when pause_ms == 0
```

Documentar en MCP_TOOLS_REFERENCE: auditoría usar `fast=true` o `pause_ms=0`.

## Test de abstracción (L4)

Presupuesto temporal aplica a cualquier app en discovery walk; no específico de Calculadora.

## Verificación de duplicados

- Sin propuesta previa para discover_target / spy_walk timeout.
- **No duplica** observe_ui_tool slow (2000ms OK) — distinto módulo.

## Esfuerzo observado

Wave_9 auditoría: 2 tools fail por timeout; agente no pudo completar fila matriz met sin hang.

## Criterio de aceptación

- [ ] discover_target max_steps=15 max_wall_ms=5000 retorna JSON <6s con timed_out o partial.
- [ ] spy_walk batch_size=10 pause_ms=0 retorna <10s en Calculadora.
- [ ] Modo highlight pause_ms=800 opt-in documentado para demos humanas.
- [ ] Matriz tool_validation puede marcar met con fast=true + timing citado.

## Beneficios futuros

- Cierra 2 de 8 fail objective_met.
- Discovery usable en loops agenticos sin colgar MCP.
- Patrón wall-clock reutilizable en otras tools pesadas.

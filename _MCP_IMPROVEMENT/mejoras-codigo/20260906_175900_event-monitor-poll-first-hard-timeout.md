# start_event_monitor: timeout sidecar y poll-first sin bloquear COM

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-06 17:59:00 |
| **Usuario sesión** | ariel.ostapow |
| **Tool afectada** | start_event_monitor, stop_event_monitor, get_event_log |
| **Módulo** | tools/event_monitor.py, tools/event_sidecar_bridge.py |
| **Tipo de gap** | performance |
| **Nivel** | L4 |
| **Versión MCP** | 0.2.1 |

## Resumen

**Problema:** En la auditoría 87 tools, `start_event_monitor` y `stop_event_monitor` devuelven
`error -32001 Request timed out` (~30s) y bloquean la sesión COM para tools posteriores.
`get_event_log` queda NA por dependencia. Bloquea `objective_met` (8 fail en matriz).

**Solución:** (1) Envolver `do_start_event_monitor` completo en executor con tope 8s y retorno
JSON de error en lugar de colgar el handler MCP. (2) Default **poll-first** cuando sidecar no
responde en ping/monitor_start (3s); documentar `AWDUI_EVENT_POLL_ONLY=1` para auditoría.
(3) Evitar `do_ui_fingerprint` en el snapshot inicial del poll loop al arrancar — diferir al
primer tick del hilo daemon. (4) `stop_event_monitor(None)` con timeout acotado en sidecar.

**Dónde:** `event_monitor.py`, `event_sidecar_bridge.py`; tests
`tests/test_event_monitor_timeout.py`; `docs/MCP_TOOLS_REFERENCE.md`.

> **Nota post-implementación (2026-09-06):** La causa raíz fue **deadlock** en
> `_ensure_server()` (`ping` dentro de `_io_lock`). Fix en `event_sidecar_bridge.py`
> + test `test_ensure_server_ping_without_deadlock`. Live: `start_event_monitor`
> ~800ms `flaui_native`. Ítems poll-first / wall-clock 8s de esta propuesta siguen
> como hardening opcional — no bloquean `objective_met`.

## Contexto del turno

- Notepad NP-12/NP-13 met; `notepad_perfect` 20/20.
- `objective_met` sigue false: 8 tool fail incl. event monitor trio; eficiencia slow sin waiver.
- Matriz: `start_event_monitor` x3 timeout; `stop_event_monitor` timeout en cadena;
  `get_event_log` NA.
- Blocker explícito en `state.json`: fix awdui-event-sidecar.

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| start_event_monitor MCP 30s | performance | L4 | Sí (este archivo) |
| stop/get_event_log en cadena | performance | L4 | Incluido |
| NP-12/13 Notepad OK | — | — | No |
| notepad_perfect true | — | — | No |

Sidecar path: `_ensure_server()` ping o `monitor_start` puede bloquear sin retorno antes del
fallback poll. El cliente MCP agota 30s aunque el código tenga `fut.result(timeout=4.0)` solo
en la rama native — otras rutas (stdin sidecar, COM en enrich) no están acotadas.

## Cambio propuesto

```python
# event_monitor.py — do_start_event_monitor
def do_start_event_monitor(...) -> dict:
    with ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(_start_event_monitor_impl, ...)
        try:
            return fut.result(timeout=8.0)
        except FuturesTimeout:
            return {
                "success": False,
                "error": "start_event_monitor exceeded 8s; use start_watcher for window polling",
                "hint": "Set AWDUI_EVENT_POLL_ONLY=1 or fix sidecar",
            }
```

```python
# event_sidecar_bridge.py — _ensure_server ping timeout 2s ya existe;
# reducir _call default timeout monitor_start a 2s; on failure skip native entirely.
```

Poll backend: no llamar `_session_snapshot` antes de `thread.start()` — el loop hace el primer
snapshot async.

## Test de abstracción (L4)

Cualquier app Windows con auditoría de eventos UIA se beneficia; no depende de Notepad ni
Calculadora.

## Verificación de duplicados

- Sin propuesta previa en `_MCP_IMPROVEMENT/` para event_monitor.
- `start_watcher` ya met en matriz — complementario, no sustituto documentado.

## Esfuerzo observado

Wave_10: 3 invocaciones start colgadas; bloqueó batch posterior; sidecar listado en blockers
desde auditoría 87 tools.

## Criterio de aceptación

- [ ] `tests/test_event_monitor_timeout.py`: mock sidecar hang → respuesta error <10s, no hang pytest.
- [ ] Live: `start_event_monitor(event_type=focus)` retorna en <8s (success poll o error JSON).
- [ ] `stop_event_monitor` sin sesión previa colgada retorna en <3s.
- [ ] Tras fallo start, `click_element` / `list_elements` siguen operativos (sin COM lock).
- [ ] Documentado en MCP_TOOLS_REFERENCE + notepad/gaps/mcp-improvements.md blocker resuelto.

## Beneficios futuros

- Desbloquea criterio `objective_met` (3 de 8 fail).
- Permite auditoría wave_10 sin recovery MCP restart.
- Patrón reutilizable: wall-clock cap en tools de sesión larga.

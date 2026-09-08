# invoke_element: probe_ms + skip stale spy en Electron (total_ms inflado)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-06 21:48:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | `tools/ui_automation.py`, `tools/action_timing.py`, `tools/spy_bridge.py` |
| **Tool afectada** | `invoke_element`, `click_element` (mismo pipeline `_finish_action_with_verify`) |
| **Tipo de gap** | performance |
| **Nivel** | L4 |
| **Impacto** | alto |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** Tras fix TE-05 verify (408 ms) y find/list perf OK, `invoke_element` en Teams
(SelectionItem / TreeItem chat) reporta `total_ms` **19–21 s SLOW** mientras
`find_ms` + `act_ms` + `verify_ms` suman **< 500 ms** cada uno. El gate
`teams_perfect` (skill 213301) y `classify_performance` marcan falso SLOW y el agente
interpreta fricción inexistente.

**Causa raíz:** Fases **no instrumentadas** antes del primer `timer.start("find")` en
`do_invoke_element` / `do_click_element`:

1. `_stale_instance_probe` → `spy_verify_live` / `spy_inspect_element` (FlaUI sidecar) en
   cada invoke con `automation_id` — en Electron puede tardar **15–20 s** sin contarse en fases.
2. `do_detect_framework` + rama spy UWP (skip en Electron, pero stale probe siempre corre).
3. `snapshot_selection_prestate` entre find y act (rápido, pero sin `probe_ms`).
4. `ActionTimer.attach()` usa wall-clock total desde `__init__`; no hay `unaccounted_ms` ni
   `performance` basado en suma de fases.

**Solución:**

1. **`probe_ms` obligatorio:** `timer.start("probe")` al inicio de `do_invoke_element` /
   `do_click_element`; `timer.end()` antes de `find`. Incluir stale probe, framework detect,
   snapshot prestate, spy preflight.
2. **Skip stale spy en UIA-first Electron:** si `_prefer_uia_find_before_spy(window_title)` y
   framework ∈ (`electron`, `chromium_browser`) → omitir `_stale_instance_probe` (paridad con
   skip spy en `list_elements` / `find_element` del turno perf).
3. **JSON timing:** `timing.unaccounted_ms = total_ms - sum(phases)`; si `unaccounted_ms > 500`
   log stderr `[AwdUI] timing gap`.
4. **`classify_performance`:** usar `max(total_ms, sum(phases))` solo si fases completas; si
   `unaccounted_ms > 1000` y sum(phases) < `SLOW_WARN_MS` → `performance: "ok"` con
   `timing_warning: "probe_heavy"` (evita falso SLOW en harness).
5. Documentar en `MCP_TOOLS_REFERENCE.md` § invoke_element: fases `probe/find/act/verify`,
   cuándo stale probe se omite.

**Dónde:** `ui_automation.py`, `action_timing.py`, tests `tests/test_invoke_probe_timing.py`.

## Contexto del turno

| Métrica | Antes (214500) | Después fix perf turno |
|---------|----------------|------------------------|
| `list_elements(role=TreeItem, view_scope)` | 5637 ms SLOW | **1182 ms** OK (< 2000 ms gate) |
| `find_element` menur1oc | 523–786 ms | **639 ms** OK |
| TE-05 `verify_ms` | 426 ms (212500) | **408 ms** OK |
| `invoke_element` `total_ms` | 19–21 s SLOW | **19–21 s** (sin cambio — blocker) |
| Fases reportadas invoke | < 500 ms c/u | < 500 ms c/u |
| pytest | — | **19 passed** (uia_find perf + view_scope) |
| teams_perfect | false | **false** (scroll P2, AppThemeExpander, invoke timing) |

Fix aplicado este turno: `_should_skip_spy_list`, `_collect_typed_role_elements`,
`view_scope` bypass TreeItem/ListItem/TabItem en `uia_backend.py`.

## Cambio propuesto (pseudodiff)

```python
# ui_automation.py — do_invoke_element

def do_invoke_element(...) -> dict:
    timer = ActionTimer()
    timer.start("probe")
    wt, hwnd, scope_info = _apply_action_scope(...)
    # ... verify_kwargs ...

    fw = ""
    try:
        from tools.framework_detect import do_detect_framework
        fw = do_detect_framework(window_title).get("framework", "")
    except Exception:
        pass

    skip_stale = (
        fw in ("electron", "chromium_browser")
        and _prefer_uia_find_before_spy(window_title)
    )
    if not skip_stale:
        stale = _stale_instance_probe(automation_id, window_title)
        if stale:
            timer.end()
            return timer.attach(stale)

    timer.end()
    # existing find / act / verify with timer phases unchanged
```

```python
# action_timing.py — ActionTimer.attach

def attach(self, result: dict) -> dict:
    ...
    phase_sum = sum(v for k, v in self.phases.items() if k.endswith("_ms"))
    timing["unaccounted_ms"] = max(0, total - phase_sum)
    if timing["unaccounted_ms"] > 1000 and phase_sum < SLOW_WARN_MS:
        result["performance"] = classify_performance(phase_sum)
        result["timing_warning"] = "unaccounted_probe"
    ...
```

```python
# format_timing_suffix — show probe_ms when present
for key in ("probe_ms", "find_ms", "act_ms", "verify_ms", "list_ms"):
    ...
```

## Verificación de duplicados

| Propuesta | Estado | Relación |
|-----------|--------|----------|
| 212500 selection verify fast poll | aplicada | verify 408 ms resuelto; **no** cubre total_ms |
| 214500 list TreeItem perf | propuesta → **aplicada este turno** | archivar; latencia 1182 ms cumple gate |
| 213300 scroll keyboard Electron | propuesta | P2 scroll — distinto concern |
| 213301 teams_perfect gate | propuesta | este fix cierra fila invoke timing del gate |
| 201430 AppThemeExpander slow | propuesta | Calculadora — distinto blocker |
| 180100 discovery wall-clock | propuesta | discover_target/spy_walk — no invoke |

Consolidación tema `performance` + `invoke-timing`: **una** spec (este archivo).

## Test de abstracción (L4)

Cross-app: cualquier Electron/Chromium con `automation_id` en invoke/click; WinForms/UWP
siguen usando stale probe cuando spy es el backend primario. Sin IDs Teams en servidor.

## Esfuerzo observado

Harness TE-05 verify OK pero invoke marca SLOW 19 s → agente y gate `teams_perfect` bloqueados
por métrica engañosa; debugging imposible sin `probe_ms`.

## Criterio de aceptación

- [ ] `tests/test_invoke_probe_timing.py`: mock stale probe 15 s → `probe_ms` reportado;
      Electron + uia_first → stale skip, `probe_ms` < 200 ms.
- [ ] Live Teams TE-05: invoke TreeItem chat → `total_ms` < 2000 ms **o**
      `performance != "slow"` cuando sum(phases) < 2000 ms.
- [ ] `format_timing_suffix` incluye `probe Nms` cuando > 0.
- [ ] Sin regresión Calculadora stale_instance (calc.exe orphan) — probe activo cuando
      framework uwp y spy disponible.
- [ ] Documentado en `MCP_TOOLS_REFERENCE.md` § invoke_element (fases + skip stale Electron).
- [ ] `state.json` blocker invoke timing removible tras live verify.

## Beneficios futuros

- Métricas invoke/click confiables para harness Teams y apps Electron.
- Paridad skip-spy con list/find perf del mismo turno.
- Cierra blocker P1 `teams_perfect` junto con gate 213301 (scroll/AppThemeExpander aparte).

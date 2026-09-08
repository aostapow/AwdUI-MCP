# run_selection_item_verify: fase rápida HWND antes de UIA pesado

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-06 21:25:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | `tools/action_timing.py`, `tools/wait_tools.py` |
| **Tool afectada** | `invoke_element`, `click_element` (post-act verify implícito) |
| **Tipo de gap** | performance |
| **Nivel** | L4 |
| **Impacto** | alto |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** Tras el fix P1 (`WindowTitle.contact`, `ChatContext.compose_ready`,
`snapshot_selection_prestate`), TE-05/TE-14 pasan verify (`✓ verified`) pero reportan
`verify_ms` ~**12 s** (SLOW) aunque `timeout_ms` está acotado a 2500 ms. Cada iteración del
poll en `run_selection_item_verify` invoca `_read_properties` → `do_get_element_properties` /
`do_find_element(role=Edit)` (8–19 s por llamada en Teams Electron). El `deadline` solo se
evalúa al inicio del `while`; una iteración puede consumir varios segundos de UIA antes del
`sleep`, superando el presupuesto nominal y bloqueando `teams_perfect`.

**Solución:** Dividir verify en fases con presupuesto real:

1. **Fase A (rápida, ~0 ms/iter):** solo `_current_window_title()` (ctypes HWND live) +
   match de `contact_needles` cada `poll_ms`; retornar `WindowTitle.contact` sin UIA.
2. **Fase B (una vez, acotada):** si Fase A no alcanza en `fast_budget_ms` (default 800),
   un único `_verify_chat_context_ready` (no en cada iteración del loop).
3. **Fase C (lenta, residual):** Header / SelectionItem solo si A+B fallan, con
   `per_iteration_max_ms` (default 500) — abortar iteración y `sleep` si se excede.
4. Respuesta incluir `verify_phases_ms: {title_poll, chat_probe, uia_poll}` para diagnóstico.

**Dónde:** `action_timing.py` (`run_selection_item_verify`), opcional helper en `wait_tools.py`
(`read_properties_fast` sin `do_find_element` por role salvo flag explícito); tests
`tests/test_selection_item_verify.py`; `docs/MCP_TOOLS_REFERENCE.md` § verify SelectionItem.

## Contexto del turno

| Paso | Resultado | Timing |
|------|-----------|--------|
| P1 fix aplicado | `snapshot_selection_prestate`, `_contact_needles_from_acted_name`, verify tras Invoke TreeItem | tests 11 passed |
| Live `menurt3` Canal General | ✓ verified | verify_ms ~12 s SLOW |
| Live `menurq9` Awamori | ✓ verified | verify_ms ~12 s SLOW |
| `find_element` TreeItem | OK | 8–19 s SLOW |
| Matriz Teams | 21/21 met | `teams_perfect` false (latency verify + list_elements) |

Regresión TE-05/TE-14 **funcionalmente resuelta**; fricción residual es performance del loop verify.

## Cambio propuesto (pseudodiff)

```python
# action_timing.py

def run_selection_item_verify(..., timeout_ms: int = 2500, poll_ms: int = 100,
                              fast_title_budget_ms: int = 800,
                              per_iteration_max_ms: int = 500) -> dict:
    t0 = time.perf_counter()
    deadline = t0 + max(timeout_ms, poll_ms) / 1000.0
    fast_deadline = t0 + fast_title_budget_ms / 1000.0
    phases = {"title_poll_ms": 0, "chat_probe_ms": 0, "uia_poll_ms": 0}

    # Phase A: HWND-only poll (no _read_properties)
    while time.perf_counter() < min(deadline, fast_deadline):
        t_iter = time.perf_counter()
        current_wt = _current_window_title(window_title)
        for needle in needles:
            if needle.lower() in current_wt.lower():
                if not pre_wt or needle.lower() not in pre_wt.lower() or current_wt != pre_wt:
                    phases["title_poll_ms"] = int((time.perf_counter() - t0) * 1000)
                    return {"verified": True, "verify_method": "WindowTitle.contact",
                            "verify_ms": phases["title_poll_ms"], "verify_phases_ms": phases, ...}
        phases["title_poll_ms"] += int((time.perf_counter() - t_iter) * 1000)
        time.sleep(poll_ms / 1000.0)

    # Phase B: single chat context probe (not per-loop)
    t_chat = time.perf_counter()
    ctx = _verify_chat_context_ready(window_title=window_title, needles=needles)
    phases["chat_probe_ms"] = int((time.perf_counter() - t_chat) * 1000)
    if ctx:
        ctx["verify_ms"] = int((time.perf_counter() - t0) * 1000)
        ctx["verify_phases_ms"] = phases
        return ctx

    # Phase C: Header / SelectionItem with per-iteration wall cap
    while time.perf_counter() < deadline:
        t_iter = time.perf_counter()
        # ... existing Header/SelectionItem logic ...
        if (time.perf_counter() - t_iter) * 1000 > per_iteration_max_ms:
            time.sleep(poll_ms / 1000.0)
            continue
        ...
```

```python
# wait_tools.py — optional
def _read_properties(..., allow_role_find: bool = True) -> Optional[dict]:
    ...
    if role and allow_role_find:
        found = do_find_element(...)  # expensive
```

## Verificación de duplicados

- **Complementa** fix P1 aplicado este turno (`WindowTitle.contact` / `ChatContext`) — la lógica
  existe pero el **orden y presupuesto** del poll provocan SLOW.
- **No duplica** `20260906_201430` (expand verify `list_elements` profundo) — distinto caller.
- **No duplica** `20260906_204701` (`list_elements` view_scope) — cubre find/list discovery;
  esta propuesta cubre **verify post-act** que reusa `do_find_element` vía `_read_properties`.
- **Consolidar** con skills `203601` / `203630`: cadenas de verify ahora en código MCP; skills
  deben documentar que el agente **no** repite verify manual si `invoke_element` ya retorna
  `verify_method` (actualizar al aplicar esta propuesta).

## Test de abstracción (L4)

Cualquier app Electron/Chromium con TreeItem nav + título de ventana que cambia al seleccionar
chat (Slack, Discord, VS Code activity bar) se beneficia del poll HWND-first sin listas de
producto. UWP NavView con Header.changed sigue en Fase C.

## Esfuerzo observado

- Verify funcional tras P1 pero ~12 s por iteración UIA pesada en Teams.
- `teams_matrix` 21/21 met; `teams_perfect` bloqueado por latency (verify + list_elements backlog).
- Tests unitarios mockean `_read_properties` — no detectan el gap de wall-clock real.

## Criterio de aceptación

- [ ] Live Teams TE-05/TE-14: `invoke_element` TreeItem chat → `verified=true`,
      `verify_method` in (`WindowTitle.contact`, `ChatContext.compose_ready`),
      `verify_ms` < **1500 ms** p95 en 3 repeticiones.
- [ ] `tests/test_selection_item_verify.py`: test que simula `_read_properties` lento (sleep 2s)
      confirma Fase A retorna antes de invocar UIA; test `verify_phases_ms` presente.
- [ ] `verify_ms` nunca supera `timeout_ms + per_iteration_max_ms` (tolerancia documentada).
- [ ] `MCP_TOOLS_REFERENCE.md` § SelectionItem verify: fases A/B/C y campos `verify_phases_ms`.
- [ ] `teams_perfect` gate: criterio latency verify documentado en harness al aplicar.

## Beneficios futuros

- `teams_perfect` alcanzable sin workarounds de verify duplicado en skill.
- Menos carga COM/UIA en loops agenticos (un chat switch ≠ 3× find_element por poll).
- Patrón reutilizable para otros `run_post_act_verify` con poll + reads pesados.

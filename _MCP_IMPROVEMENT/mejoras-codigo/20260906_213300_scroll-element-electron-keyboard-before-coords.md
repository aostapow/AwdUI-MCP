# scroll_element: teclado enfocado antes de coords en paneles Electron/WebView

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-06 21:33:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | `tools/uia_pattern_tools.py`, `detection/uia_patterns.py`, `tools/input_tools.py` |
| **Tool afectada** | `scroll_element`, `scroll` |
| **Tipo de gap** | tool_gap |
| **Nivel** | L4 |
| **Impacto** | medio |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** En Teams Electron (TE-08), `scroll_element(automation_id=message-pane-layout-a11y)`
no expone ScrollPattern usable (`ScrollPattern N/A` en WebView). El fallback aplicado en
`181200` (`scroll_fallback_coords` — rueda en centro bbox) permite marcar TE-08 **met** en
harness, pero viola el criterio de calidad MCP Teams («programático — no coords salvo gap
documentado») y deja `teams_perfect: false` con blocker explícito en `state.json`.

**Solución:** Insertar cadena **keyboard-first** genérica antes del fallback coords cuando
ScrollPattern falla o no está disponible y `detect_framework` ∈ (`electron`, `chromium_browser`):

1. Resolver contenedor scrollable (Group/Pane/Document) por `automation_id` o `name`.
2. `click_element` o focus UIA en el pane (sin coords manuales del agente).
3. Enviar `{PageUp|PageDown|Home|End}` vía `press_key_combo` según `direction`/`amount`.
4. Verificar desplazamiento con `get_tree_hash` delta o ancla `find_text` opcional en respuesta.
5. Solo si teclado no mueve contenido → `scroll_fallback_coords` existente con
   `fallback_reason` encadenado.

Respuesta JSON: `method` ∈ (`keyboard.PageDown`, `keyboard.PageUp`, `scroll_fallback_coords`, …),
`scroll_pattern_available: false`, `keyboard_attempted: true`.

**Dónde:** `uia_pattern_tools.do_scroll_element`, helper `_scroll_keyboard_focus_chain`;
tests `tests/test_scroll_element_electron_keyboard.py`; `docs/MCP_TOOLS_REFERENCE.md` §
scroll_element; skill Teams TE-08.

## Contexto del turno

| Métrica | Valor |
|---------|-------|
| P1 verify latency | TE-05 Awamori verify **426 ms** ✓ (antes ~12 s) |
| teams_matrix | 21/21 met |
| teams_perfect | false |
| Blockers state.json | find/list SLOW; **scroll N/A message pane** |
| TE-08 evidencia previa | scroll_fallback_coords + PageUp/Down OK (met harness) |

Turno actual resolvió verify post-act; scroll sigue siendo el blocker P2 de calidad operativa.

## Cambio propuesto (pseudodiff)

```python
# uia_pattern_tools.py — after ScrollPattern failure, before do_scroll coords

_ELECTRON_FW = {"electron", "chromium_browser"}

def _scroll_keyboard_focus_chain(raw, *, direction: str, amount: str, window_title: str) -> dict:
    from tools.ui_automation import do_click_element
    from tools.input_tools import press_key_combo

    focus = do_click_element(element_dict=raw, window_title=window_title, verify=False)
    if not focus.get("success"):
        return {"success": False, "error": "focus_failed"}
    key = "pagedown" if direction == "down" else "pageup"
    repeats = 2 if str(amount).lower() in ("large", "page") else 1
    for _ in range(repeats):
        press_key_combo(key)
    return {
        "success": True,
        "method": f"keyboard.{key.upper()}",
        "direction": direction,
        "repeats": repeats,
    }

def do_scroll_element(...):
    result = apply_scroll_pattern(...)
    if result.get("success"):
        return result
    fw = _framework_name(window_title)
    if fw in _ELECTRON_FW:
        kb = _scroll_keyboard_focus_chain(raw, direction=direction, amount=amount, window_title=window_title)
        if kb.get("success"):
            kb["scroll_pattern_available"] = False
            kb["fallback_reason"] = result.get("error", "ScrollPattern N/A")
            return kb
    # existing scroll_fallback_coords chain (181200)
    ...
```

## Verificación de duplicados

- **Extiende** `181200` (aplicada) — no reemplaza coords fallback; lo relega a tercer escalón.
- **No duplica** TE-08 skill workaround — propone fix MCP genérico Electron/WebView.
- **Complementa** `204701` (find/list perf) — distinto concern (scroll vs discovery walk).

## Test de abstracción (L4)

Slack, Discord, VS Code panels WebView/Chromium con ScrollPattern ausente o roto; cualquier
Electron app con message/history pane identificable por UIA Group/Document — sin IDs Teams
hardcodeados en servidor.

## Esfuerzo observado

TE-08 met con coords; evaluación honesta MCP nivel 3 = NO por scroll coords obligatorio.
Blocker persistente en `state.json` tras matriz 21/21 met.

## Criterio de aceptación

- [ ] `tests/test_scroll_element_electron_keyboard.py`: mock ScrollPattern fail + framework
      electron → `method=keyboard.PageDown` antes de coords.
- [ ] Live Teams TE-08: `scroll_element(message-pane-layout-a11y, up)` →
      `method` starts with `keyboard.`; historial older msgs visible; sin coords en respuesta
      salvo teclado fallido.
- [ ] `teams_perfect` gate: scroll message pane cuenta como programático si method=keyboard.*
- [ ] Documentado en MCP_TOOLS_REFERENCE § scroll_element (cadena ScrollPattern → keyboard → coords).
- [ ] Sin regresión Notepad/UWP `Scroll.Scroll` path (181200 tests verdes).

## Beneficios futuros

- Cierra blocker P2 scroll para `teams_perfect` sin depender de wheel coords.
- Patrón genérico reutilizable en apps Electron con historial/chat WebView.
- Alinea TE-08 con criterio «Programático» del harness Teams.

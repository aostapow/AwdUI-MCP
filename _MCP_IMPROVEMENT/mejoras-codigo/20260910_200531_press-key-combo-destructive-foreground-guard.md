# press_key_combo: guardia foreground para atajos destructivos (Alt+F4)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 20:05:31 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | `tools/input_tools.py`, `tools/target_window.py` |
| **Tool afectada** | `press_key_combo`, `send_keys` |
| **Tipo de gap** | entorno |
| **Nivel** | L4 |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** `press_key_combo` con **Alt+F4** actúa sobre la ventana **foreground** del sistema, no
sobre `set_target_window`. En F-15 el foreground era el Explorador lab (o quedó así tras abrir Edge)
y Alt+F4 cerró el target; el agente no recibió señal estructural antes de enviar la tecla.

**Solución:** Si hay target window activo y la combinación está en lista **destructiva**
(`alt+f4`, `alt+space+c`, etc.), comparar HWND/PID foreground vs target. Por defecto: **no enviar**;
retornar `blocked=true`, `reason=foreground_mismatch`, `foreground_title`, `target_title`, hint
«focus_window en ventana a cerrar o usar Ctrl+W en browser». Parámetro `allow_foreground_mismatch=true`
para escape explícito.

**Dónde:** `do_press_key_combo` / wrapper; `docs/MCP_TOOLS_REFERENCE.md` § `press_key_combo`.

## Contexto del turno

- F-15: Ayuda → Edge; recovery intentó Alt+F4; side-effect cerró lab; `improvements.jsonl` #8.
- Evidencia: `mcp-usage.jsonl` L150-152 (`press_key_combo` → `set_target_window` fail → `launch_app` partial).

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| Alt+F4 sin guard | entorno | L4 | Sí (este archivo) |
| Agente no focus Edge | routing_tool | L4 | Skill `200530` — no sustituye guard MCP |

## Cambio propuesto

```python
# input_tools.py
DESTRUCTIVE_COMBOS = frozenset({"alt+f4", "alt+space+c", ...})

def do_press_key_combo(keys: str, allow_foreground_mismatch: bool = False, **kwargs):
    combo_norm = normalize_combo(keys)
    if combo_norm in DESTRUCTIVE_COMBOS and not allow_foreground_mismatch:
        fg = get_foreground_window_info()
        tgt = get_active_target_window_info()  # from target_window.py
        if tgt and fg.hwnd != tgt.hwnd and fg.pid != tgt.pid:
            return {
                "ok": False,
                "blocked": True,
                "code": "destructive_foreground_mismatch",
                "hint": "focus_window on window to close; browser: prefer Ctrl+W",
                "foreground": fg.summary(),
                "target": tgt.summary(),
            }
    # existing send path
```

Opcional: si `combo` es Alt+F4 y `hint_process` query param (ej. `msedge`) coincide con foreground,
permitir sin flag (cerrar solo browser).

## Test de abstracción (L4)

Cualquier automatización con target pinneado que use Alt+F4 para «cerrar popup» sin focus explícito
(Notepad, Explorador, WinForms con modales + browser).

## Verificación de duplicados

| Propuesta existente | Relación |
|---------------------|----------|
| `20260906_183323` win32-client-focus (aplicada) | Skill — guard es refuerzo código |
| `20260906_183738` set-target multi-instance (aplicada) | Distinto — disambiguate título |
| Skill `20260910_200530` foreign-browser-dismiss | Hermana — documentar + guard |

## Criterio de aceptación

- [ ] `tests/test_press_key_destructive_guard.py`: mock foreground ≠ target → blocked.
- [ ] `allow_foreground_mismatch=true` envía tecla (test).
- [ ] Live F-15 replay: Alt+F4 sin focus → blocked; tras `focus_window` Edge + allow o Ctrl+W → OK.
- [ ] `docs/MCP_TOOLS_REFERENCE.md` actualizado.

## Beneficios futuros

- Fail-fast antes de matar ventana lab/producto.
- Metadata accionable para agente (hint focus) sin depender solo de narración skill.

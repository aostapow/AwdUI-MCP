# take_screenshot_optimized / annotate_screenshot — NameError `_wt` no importado

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 20:45:30 |
| **Usuario sesión** | ariel.ostapow |
| **Tool afectada** | `take_screenshot_optimized`, `annotate_screenshot` |
| **Módulo** | `mcp-servers/awdui-server/tools/screenshot.py` (`register`) |
| **Tipo de gap** | tool_gap |
| **Nivel** | L4 |
| **Versión MCP** | v0.4.0 (check_version 2026-09-10, up to date) |

## Resumen

**Problema:** En `register()` de `screenshot.py`, las tools `take_screenshot_optimized` y
`annotate_screenshot` llaman `window_title=_wt(window_title, title)` pero **`_wt` no está
importado** en ese módulo (sí en `ui_automation.py` vía `resolve_window_title`). En runtime
falla con **NameError** (`_wt`); el agente de lab F-42 usó `screenshot` como fallback (OK).

**Solución:** Importar `resolve_window_title as _wt` desde `tools.params` al inicio de
`register()` (mismo patrón que `ui_automation.py`), o usar `resolve_capture_window` /
`resolve_scope` ya presentes en el archivo para consistencia con la tool `screenshot`.
Añadir test pytest que invoque el wrapper MCP (mock `do_take_screenshot_optimized`) y
verifique que no hay NameError al resolver título.

**Dónde:** `screenshot.py` ~L1076, ~L1106; `tests/test_screenshot_tools.py` o extensión de
tests existentes de screenshot.

## Contexto del turno

- Lab `escritorio-windows-2026-09-10`, **discover_flows subárbol F-42** (panel búsqueda /
  «Búsquedas recientes»).
- OBS/ACT: `set_target_window` lab HWND; click `SearchEditBox`; `expand_element` «Búsquedas
  recientes» **1147 ms**; `get_snapshot` **130 nodos**; encolado **F-111..F-116** en `flows.json`.
- Teardown: «Cerrar búsqueda» x2; VERIFY: `screenshot` OK; **`take_screenshot_optimized` falló
  `_wt`**; `set_target_window` clear.
- Skill: `awdui-mcp-automejora`; `objective_met` false (ciclo lab global).

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| NameError `_wt` en optimized/annotate | tool_gap | L4 | **Sí (este archivo)** |
| `expand_element` ~1.1 s | performance | L3 | Backlog `expand-element-verify` — no duplicar |
| Encolado F-111..116 desde snapshot | — | — | Ejecución correcta |
| Fallback `screenshot` tras fallo optimized | ejecucion / entorno | — | Mitigación válida; fix MCP elimina necesidad |

No es `ejecucion` pura en optimized: la tool está expuesta en MCP pero **no ejecutable** sin import.

## Cambio propuesto

```python
# screenshot.py — dentro de register(), tras imports existentes:
from tools.params import resolve_window_title as _wt
```

Alternativa (alineada con tool `screenshot`):

```python
wt = resolve_capture_window(window_title, title, scope="auto")
# pasar wt a do_take_screenshot_optimized(window_title=wt, ...)
```

## Test de abstracción (L4)

Cualquier flujo que pida evidencia visual con presupuesto de tokens (`take_screenshot_optimized`)
o cajas UIA (`annotate_screenshot`) — Explorer, Teams, AST, Notepad.

## Verificación de duplicados

| Archivo | Relación |
|---------|----------|
| `20260906_202803_screenshot-background-hwnd-capture` | **Distinto** — captura HWND en background; no import `_wt` |
| `20260910_202207_click-element-hwnd-missing-do-click-import` | **Paralelo** — mismo patrón NameError en wrapper MCP |

## Esfuerzo observado

Un intento fallido de optimized en verify F-42; agente recuperó con `screenshot` (~sin bloqueo de flujo).

## Criterios de aceptación

- [ ] `take_screenshot_optimized` y `annotate_screenshot` resuelven `window_title`/`title` sin NameError
- [ ] Test pytest registra ambas tools o llama wrappers con título vacío y título mock
- [ ] `python scripts/validate_tools_reference.py` sin cambio de contrato (solo fix runtime)
- [ ] Tras fix: re-verify F-42 o smoke `take_screenshot_optimized` con target Explorer

## Beneficios futuros

- VERIFY de discover lab puede usar optimized por defecto (menor payload) sin fallback obligatorio a `screenshot`
- `annotate_screenshot` usable en hits de regresión visual sin error opaco `_wt`

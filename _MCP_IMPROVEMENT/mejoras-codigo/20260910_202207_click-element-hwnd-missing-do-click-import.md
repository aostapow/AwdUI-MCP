# click_element_hwnd — NameError `do_click_element_hwnd` no definido

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 20:22:07 |
| **Usuario sesión** | ariel.ostapow |
| **Tool afectada** | `click_element_hwnd` |
| **Tipo de gap** | tool_gap |
| **Nivel** | L4 |
| **Versión MCP** | v0.4.0 (check_version 2026-09-10, up to date) |

## Resumen

**Problema:** La tool MCP `click_element_hwnd` invoca `do_click_element_hwnd(...)` en
`ui_automation.py` pero **no importa** la función; la implementación vive en
`tools/visual_diff.py`. En runtime devuelve error tipo **NameError** (registrado en lab F-23
como «click_element_hwnd roto»).

**Solución:** Importar `do_click_element_hwnd` desde `tools.visual_diff` (import lazy dentro
del cuerpo de la tool si hiciera falta evitar carga circular — hoy `visual_diff` solo importa
`ui_automation` dentro de funciones, por lo que import top-level o lazy en `click_element_hwnd`
es seguro). Añadir test pytest que registre la tool y verifique éxito con mock de
`do_click_element_hwnd`.

**Dónde:** `mcp-servers/awdui-server/tools/ui_automation.py` (~L4196–4217);
`tests/test_ui_automation.py` o `tests/test_click_element_hwnd.py`.

## Contexto del turno

- Lab `escritorio-windows-2026-09-10`, flujo **F-23** (`partial`): «Abrir flyout Compartir (panel Enviar)».
- `flows.json` / `improvements.jsonl`: homónimo TabItem/Button «Compartir»; workaround
  `element_at_point` + click; **`click_element_hwnd` NameError** (`do_click_element_hwnd` undefined).
- `fix_in_cycle`: `not_attempted` en improvements.jsonl para este ítem.

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| NameError en `click_element_hwnd` | tool_gap | L4 | **Sí (este archivo)** |
| TabItem vs Button mismo nombre | routing_tool / deteccion | L3 | Skill separada F-23 homonym |
| Flyout Enviar poco visible UIA | deteccion | L3 | No duplicar — verify Escape + screenshot |

No es `ejecucion`: la tool está documentada en `MCP_TOOLS_REFERENCE.md` pero **no ejecutable**.

## Cambio propuesto

```python
# ui_automation.py — dentro de click_element_hwnd, antes de with_timeout:
from tools.visual_diff import do_click_element_hwnd
```

O al inicio del módulo si no hay ciclo de importación.

**Criterio pytest:**

```python
def test_click_element_hwnd_resolves_helper(monkeypatch):
    monkeypatch.setattr(
        "tools.visual_diff.do_click_element_hwnd",
        lambda *a, **k: {"success": True, "clicked_at": {"x": 1, "y": 2}},
    )
    # invocar handler registrado o importar y llamar wrapper
```

Incluir en `mcp_tools_smoke.py` registro de `click_element_hwnd` con HWND mock si ya existe patrón.

## Test de abstracción (L4)

Cualquier app multi-ventana que use `click_element_hwnd` con `window_handle` explícito.

## Verificación de duplicados

| Propuesta | Acción |
|-----------|--------|
| Búsqueda `_MCP_IMPROVEMENT` `click_element_hwnd` | **Ninguna** — gap nuevo |
| `set-target-multi-instance` | Distinto — scope ventana, no helper roto |

## Esfuerzo observado

Agente no pudo usar HWND-scoped click en F-23; escaló a coords/`element_at_point`.

## Criterios de aceptación (mantenedor)

- [ ] `click_element_hwnd` sin NameError con servidor vivo (`check_version` OK).
- [ ] Test pytest verde; `validate_tools_reference.py` sin cambio de contrato.
- [ ] Tras fix: re-VERIFY F-23 o smoke con HWND de Explorador (opcional lab).

## Beneficios futuros

HWND-scoped click usable en cintas/modales cuando `window_title` del padre no alcanza.

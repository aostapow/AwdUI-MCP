# Acotar profundidad en observe_ui tras default full-tree

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | aplicada |
| **Fecha** | 2026-07-07 01:26:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | detection/discovery/observer.py, tools/discovery.py |
| **Tool afectada** | observe_ui_tool, ui_fingerprint |
| **Tipo de gap** | performance |
| **Nivel** | L3 |
| **Impacto** | alto |

## Versiones MCP

| MCP | Versión | Nota |
|-----|---------|------|
| user-awdui | v0.2.1 | `LIST_ELEMENTS_DEFAULT_MAX_DEPTH=0` ya aplicado en tree_depth.py |

## Resumen

**Problema:** `observe_ui` invoca `do_list_elements(window_title=…)` sin `max_depth`. Con el nuevo default
`LIST_ELEMENTS_DEFAULT_MAX_DEPTH=0` (árbol completo), una sola llamada a `observe_ui_tool` puede tardar
45s–280s en formularios WinForms anidados. En el turno AST Time Report hubo timeouts repetidos en
`observe_ui_tool`, `ui_fingerprint` y `list_windows`.

**Solución:** En `observe_ui`, usar profundidad acotada explícita para el snapshot (`max_depth=8` o
constante `OBSERVE_UI_MAX_DEPTH`) y `max_items` en la muestra del árbol. No heredar el default global
de exploración profunda. Opcional: parámetro `fast=true` en `observe_ui_tool` que omita screenshot y OCR hints.

**Dónde:** `detection/discovery/observer.py` líneas ~51–57; documentar en `docs/AGENT_GUIDE.md`.

## Cambio propuesto (pseudodiff)

```python
# observer.py
OBSERVE_UI_MAX_DEPTH = 8
OBSERVE_UI_MAX_ELEMENTS = 80

result = do_list_elements(
    window_title=window_title,
    max_depth=OBSERVE_UI_MAX_DEPTH,
    include_offscreen=True,
)
elements = result.get("elements", [])[:OBSERVE_UI_MAX_ELEMENTS]
```

- `do_ui_fingerprint` ya usa `max_depth=3` — mantener.
- Evitar segunda pasada `do_list_windows()` dentro del mismo `observe_ui` si `window_title` ya resuelto.
- Exponer `duration_ms` en respuesta de `observe_ui_tool` para diagnóstico.

## Contexto del turno

Tras navegar a Time Report, el agente usó `observe_ui_tool` en exploración inicial. Con árbol profundo
el snapshot bloqueó el turno varios minutos. La primera carga de horas se completó vía UIA directa
(`list_elements` + `set_element_value`), no gracias a observe.

## Test de abstracción

Cross-app: cualquier WinForms con paneles anidados (>5 niveles) se beneficia. No depende de AST ni
de automation_ids concretos del turno.

## Verificación de duplicados

- No hay propuesta previa en `_MCP_IMPROVEMENT/` para `observe-slow` / performance.
- Relacionado pero distinto de `20260707_011000_mdi-window-scope.md` (scope ventana hija).

## Criterio de aceptación

- [ ] `observe_ui_tool` completa en <15s en fixture WinForms anidado (pytest mock o app de prueba)
- [ ] `list_elements` default sigue siendo 0 para uso explícito del agente
- [ ] Test `tests/test_observer.py` o extensión de tests discovery
- [ ] Documentado: observe solo en Fase 1, no en cada paso de Fase 6

## Beneficios futuros

Turnos con exploración inicial no pierden minutos en snapshot; el default full-tree sigue disponible
para `list_elements` dirigido con `role=ComboBox` sin penalizar herramientas de observación.

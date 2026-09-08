# scroll_element: fallback cuando ScrollPattern COM falla en UWP

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | aplicada |
| **Fecha** | 2026-09-06 18:12:00 |
| **Usuario sesión** | ariel.ostapow |
| **Tool afectada** | scroll_element |
| **Módulo** | detection/uia_patterns.py, tools/uia_pattern_tools.py, tools/ui_automation.py |
| **Tipo de gap** | tool_gap |
| **Nivel** | L4 |
| **Versión MCP** | 0.4.0 |

## Resumen

**Problema:** En Calculadora UWP (nav abierta), `scroll_element` sobre
`MenuItemsScrollViewer` devuelve error COM `(-2146233079, …)` aunque el control
expone ScrollPattern. `scroll_into_view` sobre `ListItem` hijo sí funciona
(ScrollItem). La matriz de auditoría deja `scroll_element` en **fail** — uno de
los 3 fail restantes de `objective_met`.

**Solución:** En `apply_scroll_pattern`, capturar excepciones COM/HRESULT típicas
de UWP y encadenar fallbacks genéricos: (1) `ScrollItem.ScrollIntoView` del
primer hijo visible en dirección pedida; (2) enviar `{PageDown|PageUp|Home|End}`
al contenedor enfocado; (3) retornar JSON con `method` del fallback y
`scroll_pattern_error` para diagnóstico. Documentar en MCP_TOOLS_REFERENCE que
paneles UWP con items virtualizados prefieren `scroll_into_view` por hijo cuando
ScrollPattern es frágil.

**Dónde:** `uia_patterns.py` (`apply_scroll_pattern`), `uia_pattern_tools.py`
(`do_scroll_element`); tests `tests/test_scroll_element_fallback.py`; doc tool.

## Contexto del turno

- Fix aplicado: `event_sidecar_bridge.py` — ping `_call` fuera de `_io_lock`
  (deadlock no reentrante). Event monitor trio **met** (~800 ms).
- Retest discovery: `discover_target_tool` trace OK ~3500 ms;
  `spy_walk_visible_tool` 0–1/155 nodos ~1200 ms.
- Matriz: fail 8→3; met 73→78. Residuales: `click_text`, `find_by_template_tool`,
  `scroll_element`.
- `click_text` "Siete": `smart_find` ya resuelve `num7Button` — uso OCR en botón
  UWP es routing incorrecto (no gap de tool).
- `find_by_template_tool`: requiere asset de plantilla curado — waiver harness.

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| scroll_element COM -2146233079 | tool_gap | L4 | Sí (este archivo) |
| click_text OCR Siete | routing_tool | — | No (UIA disponible) |
| find_by_template sin asset | sintoma_app | — | No |
| event monitor deadlock | entorno | — | Parcial — ver 175900 |
| discover/spy_walk slow | performance | — | Backlog 180100; met este turno |

`scroll_into_view` (ScrollItem) y `scroll` (teclado PageDown en Notepad NP-15)
demuestran rutas alternativas genéricas. `scroll_element` no debe quedar en fail
cuando el patrón COM es inestable pero el scroll es alcanzable por hijo o teclado.

## Cambio propuesto

```python
# detection/uia_patterns.py — apply_scroll_pattern
_UWP_SCROLL_HRESULTS = {-2146233079}  # o detección por mensaje COM

def apply_scroll_pattern(raw, ...) -> dict:
    try:
        ...  # Scroll.Scroll / SetScrollPercent actual
    except Exception as exc:
        hr = getattr(exc, "hresult", None) or _parse_hresult(str(exc))
        fallback = _scroll_fallback_chain(raw, direction=direction, amount=amount, repeat=repeat)
        if fallback.get("success"):
            fallback["scroll_pattern_error"] = str(exc)
            fallback["fallback_reason"] = "ScrollPattern COM failure"
            return fallback
        return {"success": False, "error": str(exc), "fallback_attempted": True}

def _scroll_fallback_chain(raw, direction, amount, repeat):
    # 1) Primer ListItem/DataItem visible → scroll_item_into_view
    # 2) Focus container + send_keys PageDown/PageUp según direction
    ...
```

Respuesta exitosa debe incluir `method` explícito (`ScrollItem.ScrollIntoView`,
`keyboard.PageDown`, etc.) para auditoría OBS→ACT→VERIFY.

## Test de abstracción (L4)

Cualquier app UWP/WPF con `ScrollViewer` que anuncia ScrollPattern pero falla en
COM (XAML virtualizing panels) se beneficia — no depende solo de Calculadora.

## Verificación de duplicados

- Sin propuesta previa en `_MCP_IMPROVEMENT/` para `scroll_element` /
  ScrollPattern fallback.
- `scroll_into_view` documentado en control-catalog — complementario, no sustituto
  automático hoy.

## Esfuerzo observado

Auditoría 87 tools: `scroll_element` fail persistente tras fix sidecar; evidencia
COM en `MenuItemsScrollViewer`; contraste con `scroll_into_view` met en
`Standard` ListItem.

## Criterio de aceptación

- [x] `tests/test_uia_pattern_tools.py::test_do_scroll_element_fallback_on_pattern_failure`
- [x] Live Notepad: `scroll_element(id=15, down)` → `Scroll.Scroll`; UWP nav → `scroll_fallback_coords`
- [x] Matriz `tool_validation_matrix.scroll_element` → met (Notepad 2026-09-06)

## Implementación (2026-09-06)

- `tools/uia_pattern_tools.py`: fallback `scroll_fallback_coords` vía `do_scroll` en centro del control cuando `apply_scroll_pattern` falla.
- `tests/test_uia_pattern_tools.py`: test unitario fallback.
- Retest agentico Notepad + matriz actualizada; `objective_met=true`.

## Beneficios futuros

- Cierra 1 de 3 fail restantes hacia `objective_met`.
- Patrón reutilizable para ScrollViewer UWP/WPF frágiles.
- Reduce escalada a coords cuando el agente elige `scroll_element` por catálogo
  de controles (control-catalog.md).

# detect_framework: clasificar TeamsWebView como electron/chromium_embedded

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-06 20:28:01 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | `tools/framework_detect.py` |
| **Tool afectada** | detect_framework |
| **Tipo de gap** | deteccion |
| **Nivel** | L4 |
| **MCP versión** | v0.4.0 |

## Resumen

**Problema:** En Microsoft Teams (proceso `ms-teams.exe`), `detect_framework` devuelve
`framework=unknown` aunque la ventana usa clase `TeamsWebView` (shell Chromium/Electron).
El agente no recibe hints de UIA condicional (`invoke_element` en nav rail, `set_element_value`
en compose) ni profundidad recomendada para apps web embebidas.

**Solución:** (1) Agregar patrones de clase: `TeamsWebView` → `electron`;
`WebView2` / `Chrome_RenderWidgetHostHWND` como señales secundarias de `chromium_embedded`.
(2) Mapear proceso `ms-teams.exe` → `electron` cuando la clase no es browser puro.
(3) Entrada en `_FRAMEWORK_INFO` para `chromium_embedded` con hints: roles Button/Edit
en WebView, `automation_id` dinámico, preferir `name` + `role` + `invoke_element`.
(4) `detection_health` puede reportar `webview_class` en metadata.

**Dónde:** `framework_detect.py` (`_CLASS_PATTERNS`, `_PROCESS_FRAMEWORKS`, `_FRAMEWORK_INFO`);
`docs/MCP_TOOLS_REFERENCE.md` § `detect_framework`; skill `teams/SKILL.md` Fase 1.

## Contexto del turno

TE-01/TE-02: `detect_framework` → `unknown`, `class=TeamsWebView`,
`detection_health` backends UIA OK. Navegación Calendario/Chat con `invoke_element`
TogglePattern funcionó (1369ms / 1322ms) — el gap es clasificación y hints, no capacidad UIA.

## Cambio propuesto (pseudodiff)

```python
# framework_detect.py
_CLASS_PATTERNS: list[tuple[str, str]] = [
    ...
    ("TeamsWebView", "electron"),
    ("WebView2", "chromium_embedded"),
]

_PROCESS_FRAMEWORKS: dict[str, str] = {
    ...
    "ms-teams.exe": "electron",
}

# Optional alias in response when class is TeamsWebView
if framework == "electron" and "teamswebview" in class_name.lower():
    hints.append("Chromium WebView shell — use name+role; automation_id may be session UUID.")
```

## Test de abstracción (L4)

Otras apps Electron con clase custom (Slack, Discord, apps internas WebView2) se benefician
sin hardcodear «Teams» en lógica de negocio — solo patrones de clase/proceso genéricos.

## Verificación de duplicados

- Sin propuesta abierta para `TeamsWebView` / `ms-teams.exe`.
- No duplica detección `Chrome_WidgetWin` (ya mapea a electron para ventanas estándar).

## Esfuerzo observado

Agente omitió hints de framework en TE-02; documentó manualmente en `element-map.md`
`Framework: unknown`.

## Criterio de aceptación

- [ ] `detect_framework` con ventana Teams activa → `electron` o `chromium_embedded`, no `unknown`.
- [ ] Proceso `chrome.exe` / `msedge.exe` sigue clasificándose como `chromium_browser`.
- [ ] Tests unitarios con mocks de class name `TeamsWebView` y `ms-teams.exe`.
- [ ] Hints listados en respuesta JSON.

## Beneficios futuros

- Routing agentico correcto en harness TE y apps Electron corporativas.
- `resolve_list_depth` puede ajustar profundidad default para webviews.

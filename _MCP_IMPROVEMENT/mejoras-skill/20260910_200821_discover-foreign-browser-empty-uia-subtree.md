# Discover: subárbol navegador ajeno sin Link UIA

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 20:08:21 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | `awdui-mcp-automejora/references/evaluacion-lab.md` + `patterns/mcp-value-filter.md` |
| **Tipo de gap** | deteccion |
| **Nivel** | L3 |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** En `discover_flows` tras `invoke_element` en un botón in-app (ej. Ayuda), la UI real
abre **msedge.exe** con contenido WebView/Bing. `list_elements(role="Link")` y controles de página
devuelven vacío o no accionables en scope UIA del MCP. El agente pierde tiempo en find negativo
(~3.7 s en discover-F-15) o encola flujos sin valor MCP (navegar enlaces Bing).

**Solución:** Protocolo discover para **ventana proceso ajeno + árbol UIA vacío**: (1) `list_windows`
clasificar nueva ventana browser vs mismo PID; (2) **no** profundizar UIA en contenido web — marcar
`skip_mcp_value` en hijos Link/Button de página; (3) encolar solo flujos **teclado** verificados
(Ctrl+W, Escape) con `focus_window` en browser; (4) persistir lección en **control in-app**:
`repo_capture` + `repo_hints_set` en el botón invoke (no path bajo Edge).

**Dónde:** Subsección en `evaluacion-lab.md` § discover subtree; enlace desde propuesta
`20260910_200530` (cierre) y `object-repository.md` (repo_path = invoke target).

## Contexto del turno

- **discover-F-15**: subárbol tras Ayuda; Edge hwnd; Link UIA vacío; F-62..F-63 cancelled con notas
  correctas; F-60 Ctrl+W pending; F-64 entry «sin subárbol UIA accionable».
- Ctrl+W probe **915 ms OK** — cierre válido (no re-proponer dismiss).
- `repo_hints_set` falló por path inexistente — ver tool `20260910_200820`.

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| WebView sin Link en scope | deteccion | L3 | Sí (este archivo) |
| find negativo ~3.7 s en Edge | routing_tool | L3 | Incluido — omitir find en contenido web |
| Ayuda→Edge (Explorador) | sintoma_app | L1 | Patrón genérico «post-invoke browser» |
| Ctrl+W OK | ejecucion | — | No |
| Alt+F4 side-effect F-15 execute | routing_tool | L4 | Cubierto por `20260910_200530` / `200531` |

## Texto propuesto

### Discover — ventana ajena tras invoke (UIA vacío)

Después de `invoke_element` en ribbon/menú:

1. `list_windows` (≤2 s): si aparece ventana **proceso distinto** (Edge, Chrome, `msedge.exe`):
   - `window_after` del flujo padre = título browser, no «panel in-app».
2. En esa ventana: **máximo** `list_elements(max_depth=2)` para confirmar vacío/sparse; si 0 `Link`
   accionables → `subtree_discovered=true` sin barrido profundo.
3. Hijos discover permitidos:
   - `press_key_combo` con focus explícito en browser (Ctrl+W preferido sobre Alt+F4 si target lab
     sigue registrado).
   - `entry` de contexto (F-64) solo para cobertura/window catalog.
4. Hijos **prohibidos** sin gap MCP nuevo: clic en enlaces Bing, descargas, formularios web.
5. Memoria: `repo_capture` del **botón invoke** en app padre → `repo_hints_set` con
   `nota: post-invoke abre browser; dismiss Ctrl+W; no UIA links en scope`.

## test_abstraccion

Cualquier Win32/UWP que abra navegador para documentación (Ayuda, «Learn more», MSDN).

## verificacion_duplicados

- **Hermana:** `20260910_200530` — foco en **cierre** post-invoke; este ítem en **discover** y
  anti-barrido UIA web.
- **Hermana:** `20260910_200531` — guard Alt+F4; no duplicar.
- Flows lab F-60/F-64 ya modelan el patrón; falta texto institucional en skill.

## beneficios_futuros

- Menos find SLOW en contenido web durante discover.
- Cola de flujos alineada con `mcp-value-filter` sin depender de notas ad-hoc en `flows.json`.

## Criterio de aceptación

- [ ] Texto sin hardcodear solo «Explorador Ayuda»; ejemplos como ilustración.
- [ ] Enlace bidireccional con `foreign-process-dismiss` / `200530`.
- [ ] discover-F-15 replay: sin find Link en Edge; hints en repo del botón Ayuda tras capture.

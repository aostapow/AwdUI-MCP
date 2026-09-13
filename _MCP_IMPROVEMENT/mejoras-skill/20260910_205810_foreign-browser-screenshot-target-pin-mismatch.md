# VERIFY screenshot con target lab fijo y navegador ajeno en primer plano

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 20:58:10 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | `awdui-mcp-automejora/references/patterns/active-window.md` + `evaluacion-lab.md` |
| **Tipo de gap** | routing_tool |
| **Nivel** | L4 |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** Tras abrir ayuda/documentación en **msedge.exe** (proceso ajeno), el lab mantiene
`set_target_window` en Explorador. `screenshot(scope=auto|window)` sin `window_title` resuelve el
**target lab** y captura el HWND del Explorador (PrintWindow / crop), no la ventana Edge visible.
En F-64 execute la evidencia `_49` fue **dudosa** aunque `list_windows` verificó el título help.

**Solución:** Patrón VERIFY para flujos `entry` de ventana ajena (F-64): (1) verify primario =
`list_windows` + título/proceso browser; (2) si hace falta PNG, `screenshot(scope=window,
window_title=<substring desde list_windows>)` **sin** cambiar target lab; (3) no usar
`screenshot(scope=auto)` como verify de contenido browser con target pinneado; (4) alternativa:
`focus_window` en browser solo para evidencia, luego restaurar foco lab.

**Dónde:** Subsección en propuesta hermana `20260910_200530` (`foreign-process-dismiss.md`) o
`evaluacion-lab.md` § execute VERIFY; una línea en `docs/AGENT_GUIDE.md` bajo evidencia visual.

## Contexto del turno

- Lab `escritorio-windows-2026-09-10`, **execute F-64** «Ventana Edge Ayuda Explorador» (parent F-15).
- ACT: click Ayuda ~1017 ms OK; VERIFY: `list_windows` detecta «get help with file explorer»
  en `msedge.exe`; cierre Ctrl+W probe 339 ms OK → flujo **met**.
- Fricción: `screenshot` outcome **dudoso** — `_49` muestra Explorador por target lab pinneado
  (`improvements.jsonl` #28; `mcp-usage.jsonl` notas «explorer pin»).
- `fix_in_cycle`: not_attempted; workaround documentado en `flows.json` / `coverage.json`.

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| PNG captura target lab, no Edge | routing_tool | L4 | Sí (este archivo) |
| list_windows verify OK | ejecucion | — | No — camino correcto |
| UIA vacío en Edge | deteccion | L3 | Cubierto por `20260910_200821` |
| Ctrl+W teardown OK | ejecucion | — | No |
| PrintWindow target en background | tool_gap | L4 | Parcial en `20260906_202803` (otro escenario) |

El parámetro `window_title` en `screenshot` ya existe (`MCP_TOOLS_REFERENCE.md`); falta patrón
lab **target fijo + ventana spawn** en skill/patterns.

## Texto propuesto

### Evidencia visual — ventana ajena con target lab activo

Cuando el flujo padre sigue registrado en `set_target_window` (Explorador u otra app lab) y la
acción abrió un **proceso distinto** (Edge, Chrome):

| Objetivo | Herramienta | Notas |
|----------|-------------|-------|
| Confirmar que abrió | `list_windows` filtrar `msedge` / título parcial | VERIFY **primario** (F-64) |
| PNG del browser | `screenshot(scope="window", window_title="<título exacto o único>")` | No omitir `window_title` |
| PNG del lab | `screenshot(scope=auto)` | Solo si verify es estado del Explorador |
| Evitar | `screenshot(scope=auto)` para «ver ayuda en Edge» | Captura target lab, no foreground |

Orden recomendado execute (entry F-64):

1. `list_windows` → guardar título ventana browser.
2. Marcar **met** si criterio de éxito es presencia de ventana (sin UIA web).
3. Screenshot opcional: `window_title` del paso 1; si falla match, `scope=full` + nota WARN
   contaminación, o omitir PNG (list_windows basta).

## test_abstraccion

Cualquier Win32 que abre navegador para ayuda/documentación mientras el harness mantiene target
en la app host (Office, IDE, Panel de control).

## verificacion_duplicados

| Archivo | Relación |
|---------|----------|
| `20260910_200530_foreign-browser-dismiss-post-invoke` | Hermana — cierre; **fusionar** esta subsección VERIFY al aplicar |
| `20260910_200821_discover-foreign-browser-empty-uia-subtree` | Hermana — discover; F-64 entry ya modelado |
| `20260906_202803_screenshot-background-hwnd-capture` | Distinta — captura target en background sin robar foco; no sustituye `window_title` explícito |

## esfuerzo_observado

Un screenshot dudoso + verify correcto vía `list_windows`; sin reintento fix en ciclo; flujo met
en ~1 s click + probe.

## beneficios_futuros

- Menos falsos FAIL/WARN en evidencia lab por PNG del target equivocado.
- Gate `perfect` / cierre honesto: distinguir harness met vs evidencia visual incorrecta.
- Agentes no escalan a `scope=full` innecesario si `window_title` alcanza.

## Criterio de aceptación

- [ ] Sin hardcodear solo «Explorador Ayuda»; msedge como ejemplo.
- [ ] Enlace desde `foreign-process-dismiss` y `evaluacion-lab.md` execute VERIFY.
- [ ] Replay F-64: PNG con título Edge o verify solo `list_windows` sin outcome dudoso.

# Explorer F-23 — ListItem vista archivos vs flyout Share; VERIFY Light Dismiss

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 20:27:08 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | `awdui-mcp-automejora/references/patterns/win32-explorer-ribbon.md` (nuevo, merge con homónimo) o `evaluacion-lab.md` § VERIFY flyout |
| **Tipo de gap** | routing_tool |
| **Nivel** | L4 |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** En el **retry** de F-23 (`partial`), `click_element` sobre **ListItem** abrió el diálogo
**«Abrir con»** (vista de archivos / menú contextual), no el flyout **Enviar** de la cinta Compartir.
`invoke_element` en ListItem pudo devolver OK sin que el shell muestre el panel Share estable.
`element_at_point` detectó **Light Dismiss** (overlay UWP), pero el flyout Share **no** aparece en
`list_windows` y el tooltip de selección no confirma compartir.

**Solución:**

1. En flujos cinta **Compartir / Enviar**, **prohibir** `click_element` / `invoke_element` con
   `role=ListItem` **sin** `ancestor_automation_id` del contenedor del comando (solo **Button** del
   grupo Enviar, ver homónimo TabItem/Button).
2. **No** usar ListItem de la lista de archivos como «probe» del flyout Share — nombres como
   «Abrir con» son acciones de ítem, no del panel lateral.
3. **VERIFY** F-23: (a) `wait_for_change` o screenshot ventana Explorador con panel lateral /
   targets de envío visibles; (b) **no** considerar éxito solo porque UIA expone `LightDismiss` /
   `Light Dismiss` — puede ser overlay genérico con flyout incorrecto o cerrado.
4. Cierre: **Escape** una vez; si persiste overlay, `element_at_point` solo para **diagnóstico**,
   no como acción de apertura.

**Dónde:** Mismo patrón `win32-explorer-ribbon.md` que
`20260910_202215_explorer-ribbon-homonym-tabitem-button.md` — **merge al implementar** (una sección
«Share / Enviar»).

## Contexto del turno

- Lab `escritorio-windows-2026-09-10`, flujo **F-23** retry, veredicto **PARTIAL**.
- `mcp-usage.jsonl`: `click_element` ListItem «Abrir con» warn; `element_at_point` Light Dismiss;
  coords `(613,172)`; `get_element_bounds` Button Compartir; probe ~1003 ms.
- `improvements.jsonl`: Share flyout UWP fuera de `list_windows`; workaround invoke + bounds +
  click centro.

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| ListItem → diálogo Abrir con | routing_tool | L4 | **Sí (este archivo)** |
| TabItem vs Button Compartir | routing_tool | L4 | `20260910_202215` — no duplicar texto |
| `click_element_hwnd` NameError | tool_gap | L4 | `20260910_202207` |
| Flyout Share opaco / HWND aparte | deteccion | L3 | Hint en `framework_detect` ya documentado — VERIFY en skill, no código nuevo |
| Light Dismiss como verify | ejecucion / routing | L3 | **Sí** — criterio VERIFY en skill |

## Texto propuesto

### Flyout Compartir (Enviar) — act y verify

| Paso | Acción | Evitar |
|------|--------|--------|
| 1 | Tab Compartir activa (TabItem o contexto F-06) | — |
| 2 | `invoke_element` / `click_element` **`role=Button`**, name del botón Enviar/Compartir del **grupo** | TabItem homónimo; **cualquier ListItem** sin ancestor |
| 3 | VERIFY | screenshot `scope=window` o `wait_for_change`; panel lateral / iconos de destino legibles | Solo `LightDismiss` en hit-test |
| 4 | Cerrar | `press_key` Escape; no enviar | Clic en ListItem «Abrir con», Bluetooth, etc. |

**Regla ListItem:** Si el objetivo es la **cinta** o un **flyout de comando**, los ListItem del
**ItemsView** (archivos, «Abrir con», «Comprimir…») están **fuera de scope** — filtrar con
`list_elements(role="ListItem", ancestor_automation_id=…)` solo cuando el discover señaló ese
ancestor en el subárbol de cinta.

## Test de abstracción (L4)

Cualquier Explorador / shell con cinta contextual + lista de archivos: confundir ListItem de vista
con comandos de ribbon es cross-app (Office, diálogos con lista + toolbar).

## Verificación de duplicados

| Propuesta | Acción |
|-----------|--------|
| `20260910_202215_explorer-ribbon-homonym-tabitem-button` | **Merge** — añadir subsección ListItem + VERIFY Light Dismiss |
| `20260907_232300_discover-root-flyout-dismiss-hygiene` | Complementaria — discover raíz UWP; no merge |
| `20260910_195126_discover-subtree-flyout-menuitem-scan` | Complementaria — MenuItem flyout contextual |

## Esfuerzo observado

Retry F-23: dos pasadas PARTIAL; coords; flyout intermitente; verify tooltip selección insuficiente.

## Criterios de aceptación (mantenedor)

- [ ] Texto sin coords del lab salvo ejemplo genérico «click centro del Button vía bounds».
- [ ] VERIFY explícito: Light Dismiss **no** es criterio de éxito F-23.
- [ ] Re-VERIFY F-23 tras merge con homónimo + fix HWND.

## Beneficios futuros

Menos diálogos «Abrir con» accidentales; criterio `met` estable para flyouts shell opacos a UIA.

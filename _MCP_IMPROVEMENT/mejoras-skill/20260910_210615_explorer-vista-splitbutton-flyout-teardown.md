# Explorer cinta Vista — teardown flyout SplitButton (Ordenar/Agrupar)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 21:06:15 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | `awdui-mcp-automejora/references/evaluacion-lab.md`, `patterns/win32-explorer-ribbon.md` (merge con hermanas) |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Versión MCP** | v0.4.0 (check_version 2026-09-10, up to date) |

## Resumen

**Problema:** En execute lab **F-71** («Abrir flyout Ordenar por»), `expand_element` en
`SplitButton: Ordenar por` abrió el menú OK (**1357 ms**), pero **`press_key` Escape ×2 no
cerró** el flyout con `focus_policy=minimal`. El cierre requirió **click probe** en la lista de
archivos (**~4591 ms**). Los `success_criteria` del flujo y el bloque «Cierre: Escape» en
`20260910_200930_explorer-vista-ribbon-vistas-verify-routing.md` no coinciden con el shell
Explorer para flyouts de ordenamiento en cinta Vista.

**Solución:** Documentar **cascada de teardown** para flyouts **SplitButton** en cinta Vista
(Ordenar por, Agrupar por — F-71/F-72), distinta del botón «Vistas» (galería layout):

1. Tras VERIFY del flyout abierto, cerrar **sin** cambiar orden/agrupación.
2. **Orden:** (a) `click_element` en área neutra del **ItemsView** / lista de archivos (probe
   lab) o `invoke_element` en **Light Dismiss** si aparece en snapshot con bbox en client rect;
   (b) si persiste menú `Window: Ordenar por`, `focus_window` Explorador + Escape **una vez**;
   (c) verify con `element_exists` negativo sobre título de flyout o `get_snapshot` sin
   `MenuItem` huérfanos del popup.
3. **No** marcar FAIL de execute si el flyout se cerró por click probe pero Escape falló —
   actualizar criterio lab a «flyout cerrado; probe intacto» (no «Escape obligatorio»).
4. Tras workaround: `repo_hints_set(append=true)` — `nota: Vista SplitButton flyout — Escape
   unreliable minimal focus; dismiss via list probe`.

**Dónde:** § «Explorer — cinta Vista» en `evaluacion-lab.md`; **merge al aplicar** con
`200930` (añadir subsección SplitButton vs botón Vistas) y `210330` (teardown ribbon flyout).

## Contexto del turno

- Lab `escritorio-windows-2026-09-10`, **F-71** `met`, parent **F-18**.
- Pre: `invoke_element` **TabItem Vista** **2037 ms** (WARN SLOW; ya en `improvements.jsonl`).
- ACT: `expand_element` Ordenar por **1357 ms** OK.
- VERIFY: ventana «Ordenar por» + MenuItems; screenshot `_52.png`.
- Teardown: Escape fail; click probe OK.

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| Escape ×2 no cierra flyout Ordenar por | routing_tool | L3 | **Este archivo** |
| invoke TabItem Vista 2037 ms | performance | L3 | **No** — evidencia G6; backlog invoke/verify tab (pass7 ~2048 ms); workaround snapshot si ya en Vista |
| expand 1357 ms | — | — | No — bajo umbral slow |
| Criterio lab «Escape cierra» desalineado | routing_tool | L3 | Incluido en solución (texto flows al aplicar skill) |

## Texto propuesto

### Vista — flyouts SplitButton (Ordenar por / Agrupar por)

**ACT:** `expand_element(name="Ordenar por", role="SplitButton")` o `invoke_element` según
`discover_control_interaction` — no confundir con ListItem de la vista de archivos.

**VERIFY:** Popup con `MenuItem` de columnas o título de ventana flyout visible.

**TEARDOWN (obligatorio):**

| Paso | Acción | Verify |
|------|--------|--------|
| 1 | Click en zona vacía del listado de archivos (probe) **o** Light Dismiss visible | Flyout ausente en snapshot |
| 2 | Si persiste | `focus_window` Explorador; `{Escape}` una vez |
| 3 | Si persiste | `click_element` TabItem Vista (re-anchor focus) + probe lista |

**Prohibido:** asumir que Escape cierra todos los flyouts ribbon con `focus_policy=minimal`.

## Test de abstracción (L3)

Cualquier ribbon Win32 con SplitButton que abre menú contextual (Office, Explorador Inicio
«Nuevo elemento»): mismo orden teardown — alinear con `210330` al implementar.

## Verificación de duplicados

| Propuesta | Relación |
|-----------|----------|
| `20260910_200930_explorer-vista-ribbon-vistas-verify-routing` | **Merge** — corregir § Cierre solo para botón Vistas; añadir SplitButton |
| `20260910_210330_discover-ribbon-splitbutton-snapshot-offscreen` | **Merge** — misma familia teardown Escape+probe |
| `20260910_210330_menuitem-include-offscreen-post-expand-discovery` | Complemento código — no duplicar |
| `20260907_232300_discover-root-flyout-dismiss-hygiene` | Raíz UWP; referencia cruzada |

## Esfuerzo observado

~4.6 s en dismiss por click tras Escape fallido; criterio success mencionaba Escape.

## Criterio de aceptación

- [ ] Texto sin IDs F-71 obligatorios (ejemplo genérico Ordenar/Agrupar).
- [ ] `evaluacion-lab.md` distingue galería «Vistas» vs SplitButton ordenamiento.
- [ ] Replay F-71/F-72: teardown < 2 s sin depender de Escape si probe cierra en &lt;1 s.

## Beneficios futuros

F-72 Agrupar por y discover subárbol F-71 sin falsos FAIL por Escape; menos tiempo en
teardown; alinea `success_criteria` flows con comportamiento shell real.

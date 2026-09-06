# Calculadora Graficar — GraphingControl, zoom UIA y vista ecuación

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-05 12:19:00 |
| **Skill objetivo** | awdui-flow-exploration/patterns/calculator-lab.md |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Impacto** | medio |

## Resumen

**Problema:** En inventario Graficar, zoom y ecuación funcionaron vía UIA (`zoomInButton`
Invoke; eje verificado en `GraphingControl.name`; `xButton`+`submitButton`). El inventario
quedó **partial** porque tras submit la vista ecuación **oculta** el gráfico y el agente
no verificó el conteo de ecuaciones en `GraphingControl` (pendiente «1 ecuación»). No
intentó `graphViewButton` ni `list_elements(include_offscreen=true)` sobre
`GraphingControl` antes de escalar a relaunch por instancia stale.

**Solución:** Sección «Modo Graficar» en `calculator-lab.md` con protocolo dual-vista,
lectura de estado compuesto vía `name`, y checklist de controles restantes.

**Dónde:** `patterns/calculator-lab.md` — subsección «Graficar (GraphingControl)».

## Contexto del turno

`calc_object_inventory_graphing`: nav Graphing 302 ms; 32 elems; zoomIn → eje ±9.41
(UIA name); SwitchModeToggle equation 265 ms; MathRichEditBox ids + x+submit OK.
Pending: GraphingControl «1 ecuación»; zoomOut/settings/tracing/inequality/y.
Blocker stale calc (relaunch manual). Skills leídas (harness + flow-exploration).
MCP v0.2.1.

**Turno seguimiento `calculator_exhaustive_act_verify` Graphing (2026-09-05 20:45):**
`reuse` calc Alt+3; `zoomInButton` re-verify ejes ±9.41 ✓ (501 ms). Desigualdad:
`inequalityButton` On + `lessThanFlyoutButton` + `x` + `0` + `submit` invoke OK (461 ms)
pero verificación leyó `GraphingControl` **0 ecuaciones** — omitió gate vista gráfico (paso 5).
`yButton` → stale tras `SwitchModeToggle` (521 ms). Screenshot `awdui_1788651871390_16.png`.
Skills: `awdui-mcp-objective`, `calculator-mcp-harness` (sin `awdui-flow-exploration`).

**Turno cierre submit x + Programador bitwise (2026-09-05 20:47):**
`reuse=true` (sin `replace`); `clear` + `xButton` + `submitButton` (497 ms). Tras submit,
`GraphingControl.name` **permanece** `0 ecuaciones` incluso con gráfico visible en screenshot
(línea `y=x`). Verificación correcta: `EquationButton` → `name` **«Ocultar ecuación 1»**
(Button accesible, no Custom). **No usar `GraphingControl` para conteo de ecuaciones** —
propiedad `name` no se invalida/actualiza vía UIA cacheada (ver `120902`). Screenshot
`awdui_1788652036967_18.png`. Alt+4 Programador: `5 AND 3=` → 1 ✓ (731 ms); `5 XOR 3=` → 6 ✓
(717 ms) en misma sesión reuse.

## Texto propuesto

### Modo Graficar — GraphingControl y ecuaciones

| Señal | automation_id / rol | Pattern | Verificación UIA |
|-------|---------------------|---------|------------------|
| Vista gráfico | `GraphingControl` | Custom — **estado en `name` (solo ejes)** | Eje (`0..0` → `±9.41` tras zoom) — **no** confiar en conteo ecuaciones |
| Ecuación activa | `EquationButton` | Button — **estado en `name`** | Tras submit: «Ocultar ecuación 1» / «Ocultar ecuación N» (locale ES) |
| Zoom in/out | `zoomInButton`, `zoomOutButton` | Invoke | Re-leer `GraphingControl.name` (no OCR) |
| Vista ecuación | `SwitchModeToggleButton` | TogglePattern | Aparecen `MathRichEditBox`, `EquationInputList`, `xButton`, `yButton`, `submitButton` |
| Entrada variable | `xButton`, `yButton` | Invoke | Preferir botones sobre `set_element_value` en `MathRichEditBox` |
| Enviar ecuación | `submitButton` | Invoke | Tras submit → **cambiar vista** antes de verificar gráfico |
| Volver al gráfico | `graphViewButton` | Invoke | Luego `spy_inspect(GraphingControl)` o `list_elements(automation_id=GraphingControl, include_offscreen=true)` |

**Protocolo OBS→ACT→VERIFY (ecuación):**

1. `invoke_element` `SwitchModeToggleButton` → Toggle On.
2. `invoke_element` `xButton` (o `yButton`) → `invoke_element` `submitButton`.
3. **VERIFY (obligatorio — señal primaria):** `spy_inspect(automation_id=EquationButton)` o
   `get_element_properties` → `name` debe contener **«Ocultar ecuación 1»** (o N) tras submit.
4. **VERIFY secundario (opcional):** screenshot `scope=window` con línea de ecuación visible
   en rejilla; `GraphingControl.name` para **ejes** tras zoom, no para conteo.
5. **No** usar `GraphingControl` conteo (`0 ecuaciones` / `1 ecuación`) — UIA devuelve
   **name stale** post-submit (turno 2026-09-05 exhaustive: submit OK + gráfico visible +
   `GraphingControl` sigue `0 ecuaciones`).

**Anti-patrón:** Asumir fallo MCP si `GraphingControl.name` no cambia el conteo tras submit —
usar `EquationButton.name`. Asumir fallo si `GraphingControl` no aparece en vista ecuación
(offscreen/hidden) — distinto del stale de conteo.

**Checklist inventario pendiente (post exhaustive 2026-09-05):**

- `zoomOutButton` (simétrico a zoomIn — zoomIn re-verificado live)
- `GraphSettingsButton`, `ActiveTracing` (inventario inicial met; act+verify individual opcional)
- ~~`greaterThanOrEqualFlyoutButton`~~ — **met** (y>=0, 579 ms)
- ~~`graphViewButton` toggle round-trip~~ — **met** (567 ms)
- `EquationInputList` hijos tras múltiples ecuaciones

### Modo desigualdad (inequality flyout)

| Señal | automation_id | Pattern | Notas |
|-------|---------------|---------|-------|
| Tipo desigualdad | `inequalityButton` | **TogglePattern** | On antes de elegir operador |
| Operadores flyout | `lessThanFlyoutButton`, `lessThanOrEqualFlyoutButton`, `equalsFlyoutButton`, `greaterThanFlyoutButton`, `greaterThanOrEqualFlyoutButton` | Invoke | Descubrir con `list_elements` tras toggle On (~10s en árbol grande — usar `automation_id` directo) |
| Variable / valor | `xButton` o `yButton`, `num0Button`… | Invoke | Igual que ecuación simple |
| Enviar | `submitButton` | Invoke | **No** verificar `GraphingControl` en vista ecuación |

**Protocolo OBS→ACT→VERIFY (desigualdad x < 0):**

1. `invoke_element` `SwitchModeToggleButton` → vista ecuación On.
2. `invoke_element` `inequalityButton` → Toggle On.
3. `invoke_element` `lessThanFlyoutButton` (o `greaterThanFlyoutButton`).
4. `invoke_element` `xButton` → `num0Button` → `submitButton`.
5. **VERIFY (obligatorio):** `spy_inspect(automation_id=EquationButton)` → `name` contiene
   **«Ocultar ecuación 1»** (señal primaria; no depende de vista gráfico/ecuación).
6. Screenshot `scope=window` con rejilla y línea de desigualdad/ecuación visible.
7. **Opcional** (solo ejes): `GraphingControl.name` para zoom — **no** para conteo ecuaciones.

**Anti-patrón (turnos 2026-09-05 20:45 y 20:47):**
- Leer `GraphingControl` conteo tras submit → falso «0 ecuaciones» aunque ecuación está activa.
- Omitir `EquationButton` como verify — el Button sí refleja ecuación N en `name`.
- Confiar en gate vista gráfico para conteo — innecesario si `EquationButton` responde.

**Stale post-toggle:** tras `SwitchModeToggleButton`, re-`list_elements` o `spy_inspect` antes de
`yButton` / `xButton` (ver consolidación `120902_stale-element-cache`).

## Evidencia adicional — turno greaterThanFlyout y>0 (2026-09-05 20:53)

**Escenario:** `launch_app` `reuse=true` (sin `replace`); modo Graficar; desigualdad
`greaterThanFlyoutButton` + `yButton` + `submitButton` invoke OK.

**VERIFY (patrón confirmado):** `EquationButton.name` → **«Ocultar ecuación 1»** tras submit
(señal primaria; no `GraphingControl` conteo). Misma sesión reuse sin relaunch.

**Checklist actualizado:** `greaterThanFlyoutButton` + `yButton` + submit verificados live;
pendiente en Graficar: `zoomOutButton`, `GraphSettingsButton`, `ActiveTracing`,
`EquationInputList` multi-ecuación.

**Fricción:** ninguna estructural — ejecución alineada con protocolo `EquationButton` de esta
propuesta y policy `reuse` documentada en harness.

## Evidencia adicional — turno lessThanOrEqual + equalsFlyout (2026-09-05 20:53)

**Escenario:** `launch_app` `reuse=true` (sin `replace`); modo Graficar; misma sesión tras
`greaterThanFlyout` + `yButton`.

**ACT+VERIFY (patrón confirmado):**

| Control | Flujo | Verify | ms |
|---------|-------|--------|-----|
| `lessThanOrEqualFlyoutButton` | inequality On → `x<=0` → submit | `EquationButton` «Ocultar ecuación 1» | 610 |
| `equalsFlyoutButton` | clear → inequality → `x=1` → submit | screenshot línea **vertical x=1** (`awdui_1788652452902_23.png`) | 562 |

**Notas:**

- `spy_inspect(lessThanOrEqualFlyoutButton)` expone `name` **«Menor o igual que»** — usar
  `automation_id` directo tras `inequalityButton` Toggle On (evitar barrido lento del árbol).
- Para `equalsFlyout` (ecuación vertical), screenshot en vista gráfico es verify válido cuando
  la línea es inequívoca (x=1); `EquationButton` sigue siendo señal primaria para conteo.
- **Inequality flyout 6/6 met** (2026-09-05 20:54): `greaterThanOrEqualFlyoutButton` +
  `y>=0` → submit (579 ms) → `EquationButton` «Ocultar ecuación 1» ✓.

**Fricción:** ninguna estructural — protocolo dual-verify (`EquationButton` + screenshot canvas)
alineado con sección desigualdad de esta propuesta.

## Evidencia adicional — turno greaterThanOrEqual + graphViewButton (2026-09-05 20:54)

**Escenario:** `launch_app` `reuse=true` (sin `replace`); modo Graficar; misma sesión tras
`lessThanOrEqualFlyout` + `equalsFlyout`.

**ACT+VERIFY (cierre exhaustive Graficar):**

| Control | Flujo | Verify | ms |
|---------|-------|--------|-----|
| `greaterThanOrEqualFlyoutButton` | inequality On → `y>=0` → submit | `EquationButton` «Ocultar ecuación 1» | 579 |
| `graphViewButton` | Toggle On → Off → On round-trip | `spy_inspect` Toggle state Off then On ✓ | 567 |

**Notas:**

- `greaterThanOrEqualFlyoutButton` cierra inequality flyout **6/6** (lessThan, lessEqual,
  equals, greaterThan, greaterEqual — todos verificados con `EquationButton` o screenshot).
- `graphViewButton` usa **TogglePattern** — verificar por cambio de estado Toggle
  (`Off`/`On`), no por `name` estático.
- **Graphing exhaustive act+verify:** met en `state.json` (inequality + graphView + zoom/submit
  previos). Pendientes harness §C: conversores `Units1`/`Units2` act+verify individual,
  Settings expanders ya cubiertos en inventario.

**Fricción:** ninguna estructural — ejecución alineada con protocolo dual-vista y policy
`reuse` documentada en harness.

### Patrón cross-app (WinUI)

Controles custom que codifican estado en `name`/`HelpText` (ejes, contadores): leer
`get_element_properties` / `spy_inspect` **después** de la acción; no depender de
screenshot salvo canvas sin texto UIA.

## Verificación de duplicados

- Distinto de `121301_calculator-flyout-expandcollapse` (Científica Toggle flyouts).
- Distinto de `120902_stale-element-cache` (entorno COM — no duplicar; ver consolidación).
- Complementa `calculator-mcp-harness` sección C tabla Graficar (checklist operativo).

## Test de abstracción

Aplica a apps WinUI con paneles mutuamente excluyentes y estado en `name` accesible
(no solo Calculadora). L3 cross WinUI.

## Criterio de aceptación

- [ ] Texto en `calculator-lab.md` sin depender de turno concreto
- [ ] Verify post-submit documenta `EquationButton.name` como señal primaria (no `GraphingControl` conteo)
- [ ] Anti-patrón `GraphingControl.name` stale documentado
- [ ] Checklist controles Graficar pendientes referenciado desde harness si aplica

## Beneficios futuros

- Cierra inventario Graficar sin OCR ni coords para zoom/ecuaciones.
- Reduce falsos «Graphing partial» por vista ecuación oculta.
- Modelo reutilizable para otros custom controls con estado textual UIA.

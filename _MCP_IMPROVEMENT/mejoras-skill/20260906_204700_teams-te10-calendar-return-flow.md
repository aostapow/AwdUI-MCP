# Teams TE-10: calendario vista día + retorno Chat Awamori

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-06 20:47:00 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | teams |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** TE-10 **met** (vista día Calendario + retorno chat Awamori con `[AwdUI-MCP-TE]`
visible), pero el flujo actual es un stub de 3 líneas y el agente pagó latencia evitable:
`list_elements(role=Button)` → 81 controles en **4637 ms** (SLOW) solo para inventario; retorno
vía `invoke_element(menur1aq)` con id rotado (`menurfp`→`menur1aq`); verify historial
`find_text` **9494 ms**. SelectionItem verify sigue el patrón WARN de TE-05.

**Solución:** Documentar flujo TE-10 OBS→ACT→VERIFY copiable en `TE-10-calendar.md` y
`element-map.md` § Calendario:

1. **Verify calendario** — título ventana `Calendar|Microsoft Teams` + `find_text("Calendario")`
   + screenshot día (grid horario). **No** usar `list_elements(role=Button)` salvo diagnóstico
   TE-02; prohibido invocar Nuevo / Reunirse ahora.
2. **Retorno Chat** — reutilizar secuencia TE-09 (`NAV-CHAT-RETURN` TogglePattern) +
   `scroll_into_view(name~="Awamori", role="TreeItem")` antes de invoke si offscreen.
3. **Localizar chat** — `find_element(name~="Awamori", role="TreeItem")`; hint id rotativo
   `menur1aq` (post TE-09 `menurfp`) solo en element-map, no en pasos obligatorios.
4. **Verify historial** — preferir `element_exists` / `find_element` con prefijo `[AwdUI-MCP-TE]`
   en burbuja antes de `find_text` full-window; verify header ListItem Awamori.

**Dónde:** `.cursor/skills/teams/flows/TE-10-calendar.md`, `teams/element-map.md` § TE-10,
`teams/gaps/mcp-improvements.md` (fila verify historial lento post-calendario).

## Contexto del turno

| Paso | Tool / señal | Resultado |
|------|--------------|-----------|
| Nav calendario | `invoke_element` `ef56c0de` TogglePattern | OK ~1406 ms |
| Inventario | `list_elements(role=Button)` | 81 els, **4637 ms** SLOW |
| Verify vista | `find_text` Calendario + screenshot `_33` | día 6 Sept 2026 OK |
| Retorno | nav Chat `3b64df9d` + invoke `menur1aq` | chat restaurado |
| Verify harness | `find_text` `AwdUI-MCP-TE` + screenshot `_35` | met |
| Fricción | TreeItem id rotation; SelectionItem verify fail pattern | WARN documentado |

Evidencia: `state.json` teams_matrix TE-10 met; screenshots `_33`, `_35`.

## Esfuerzo observado

~4,6 s en list_elements innecesario para verify de vista; ~9,5 s en find_text post-retorno;
riesgo de depender de id `menu*` stale en pasos TE-11+ si no se documenta patrón name-first.

## Texto propuesto

### TE-10 — Calendario vista día (pasos)

```
OBS: set_target_window Teams; chat Awamori abierto (TE-05/07)
ACT calendario: invoke_element(name="Calendario", role="Button")  # ef56c0de hint
VERIFY vista (sin list_elements Button salvo TE-02 discovery):
  - window title contiene "Calendar" y "Microsoft Teams"
  - find_text("Calendario") en ventana objetivo
  - screenshot: grid día + mini-calendario (ej. 6 Sept 2026)
  - NO invoke "Nuevo" / "Reunirse ahora"

ACT retorno: invoke_element(name="Chat", role="Button")  # NAV-CHAT-RETURN
VERIFY vista chat (no Calendar title)

ACT reabrir chat (misma secuencia TE-09):
  1. scroll_into_view(name~="Awamori", role="TreeItem")  # si invoke falla/offscreen
  2. invoke_element(name~="Awamori", role="TreeItem", verify_name_contains="Awamori")
VERIFY historial:
  - element_exists / find_element con [AwdUI-MCP-TE] en burbuja (preferido)
  - find_text solo fallback; header ListItem Awamori visible
```

### Quirk § (element-map TE-10)

«Ids sidebar `menurfp` (TE-09) → `menur1aq` (TE-10) rotan al cambiar sección Calendario↔Chat;
localizar siempre por `name` + `role=TreeItem`. Nav Chat no restaura chat activo — ver TE-09.»

## Test de abstracción

L3: apps Electron con nav rail + sidebar virtualizada (Slack, Discord) — verify de vista por
título + OCR acotado + retorno con scroll_into_view; no hardcodea solo Teams salvo hints en
element-map.

## Verificación de duplicados

- **Complementa** `204500` (TE-09 retorno scroll TreeItem) — TE-10 reutiliza misma secuencia
  post-Calendario; merge al aplicar ambos en `teams/flows/`.
- **Complementa** `203630` (TE-05 TreeItem verify header) — SelectionItem WARN y name-first.
- **No duplica** `203601` (verify compose vs historial) — TE-10 verify es historial post-retorno.
- `list_elements` SLOW: backlog P2 en gaps + propuesta código `204701` (view scope Electron).

## Beneficios futuros

- TE-10 repetible sin barrido Button 4–5 s ni find_text 9 s por defecto.
- Matriz TE-11+ hereda patrón retorno nav rail documentado.
- Harness `met` con workaround explícito hasta fix MCP view-scope (nivel calidad operativa).

## Criterio de aceptación

- [ ] `TE-10-calendar.md` con bloque OBS/ACT/VERIFY copiable (no stub 3 líneas).
- [ ] `element-map.md` § TE-10 enlaza NAV-CHAT-RETURN + hint `menur1aq` rotativo.
- [ ] `gaps/mcp-improvements.md` fila «find_text historial lento post-calendario» P2.
- [ ] Sin `list_elements(role=Button)` como paso obligatorio de verify TE-10.

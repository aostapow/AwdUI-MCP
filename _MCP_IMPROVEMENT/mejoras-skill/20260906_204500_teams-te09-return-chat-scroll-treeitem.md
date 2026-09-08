# Teams TE-09: retorno Chat + scroll_into_view TreeItem offscreen

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-06 20:45:00 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | teams |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** TE-09 **met** (equipo Testing Accusys → canal General lectura, sin Publicar), pero al
volver a Chat vía nav rail (`Chat` TogglePattern) el chat Awamori **no** se restaura solo. El
TreeItem de la lista (`menurfp`, id rotativo) queda offscreen; hace falta `scroll_into_view` antes
de `invoke_element` para reabrir el chat harness.

**Solución:** Expandir flujo TE-09 y `element-map.md` § Equipos/canales con pasos OBS→ACT→VERIFY
y secuencia de retorno obligatoria:

1. Tras `invoke_element` nav **Chat** — verificar vista chat (no canal).
2. `find_element(name~="Awamori", role="TreeItem")` — si invoke falla o elemento offscreen →
   `scroll_into_view(name~="Awamori", role="TreeItem")` **antes** de invoke.
3. `invoke_element` TreeItem + verify header ListItem / mensaje harness `[AwdUI-MCP-TE]` visible.
4. Canal General: verify ausencia compose `Escribe un mensaje` y **no** invocar **Publicar en el canal**.

**Dónde:** `.cursor/skills/teams/flows/TE-09-teams-channels.md`, `teams/element-map.md` § TE-09,
`teams/gaps/mcp-improvements.md` (fila offscreen post-canales).

## Contexto del turno

| Paso | Tool / señal | Resultado |
|------|--------------|-----------|
| Ir equipos | `invoke_element` Equipos y canales | OK |
| Canal General | `invoke_element` `menurhl` SelectionItem | OK |
| Lectura | sin compose; sin Publicar; `find_text` General | OK read-only |
| Volver Chat | nav `Chat` TogglePattern (`3b64df9d-…`) | vista Chat, chat previo no restaurado |
| Retorno Awamori | `scroll_into_view` `menurfp` → invoke | OK ~1463 ms total TE-09 |
| Verify | header Awamori + burbuja `[AwdUI-MCP-TE]` | met |

Evidencia: screenshots `_25`, `_26`, `_30`; `state.json` teams_matrix TE-09 met.

## Esfuerzo observado

Un paso extra de `scroll_into_view` en retorno; sin él el TreeItem no es accionable. Nav Chat no
equivale a «volver al chat anterior» en Teams Electron.

## Texto propuesto

### TE-09 — Equipos/canales lectura (pasos)

```
OBS: set_target_window Teams; chat Awamori ya abierto (TE-05/07)
ACT equipos: invoke_element(name="Equipos y canales", role="Button")
VERIFY: vista equipos/canales visible

ACT canal: invoke_element(name~="General", role="TreeItem")  # menurhl hint
VERIFY read-only:
  - element_exists(name="Escribe un mensaje", role="Edit") → FAIL esperado
  - NO invoke_element "Publicar en el canal"
  - título ventana contiene "General" (opcional)

ACT retorno: invoke_element(name="Chat", role="Button")  # NAV-CHAT-RETURN
VERIFY vista chat (no canal)

ACT reabrir chat:
  1. scroll_into_view(name~="Awamori", role="TreeItem")   # obligatorio si offscreen
  2. invoke_element(name~="Awamori", role="TreeItem", verify_name_contains="Awamori")
VERIFY: header ListItem Awamori; historial con [AwdUI-MCP-TE] si TE-07 previo
```

### Quirk § (teams/SKILL.md o element-map)

«Tras salir de vista Equipos/canales, el nav Chat cambia de sección pero **no** restaura el chat
activo; localizar TreeItem por `name` + `role` y usar `scroll_into_view` si el item no está en
viewport (ids `menu*` rotan — ver TE-05).»

## Test de abstracción

L3: listas virtualizadas en sidebars Electron (Slack, Discord) requieren `scroll_into_view` antes
de invoke tras cambio de contexto de navegación; el texto no hardcodea solo Teams salvo hints en element-map.

## Verificación de duplicados

- `203630` (TE-05 TreeItem verify): complementario — abrir chat inicial vs reabrir tras TE-09; merge en skill `teams` al aplicar ambos.
- `203601` (verify chains): no cubre secuencia retorno post-canales.
- `scroll_into_view` ya documentado en `control-catalog.md` — falta **cuándo** en flujo Teams TE-09.
- Backlog `181200` (`scroll_element` COM fallback): TE-08; TE-09 usó `scroll_into_view` (ScrollItem) con éxito.

## Beneficios futuros

- Segundo pase TE-09 sin re-descubrir offscreen en retorno.
- `teams_perfect` con workaround documentado (nivel harness) hasta que nav restaure chat (sintoma app).

## Criterio de aceptación

- [ ] `TE-09-teams-channels.md` con bloque OBS/ACT/VERIFY copiable.
- [ ] `element-map.md` § NAV-CHAT-RETURN enlaza paso `scroll_into_view` post-TogglePattern.
- [ ] `gaps/mcp-improvements.md` fila «TreeItem offscreen tras canales» P2.
- [ ] Sin depender de `automation_id` fijo en pasos obligatorios (solo hints).

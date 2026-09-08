# Teams TE-05/TE-06: cadenas de verify cuando UIA Electron es stale

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-06 20:36:01 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | teams |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** En TE-05 el chat Awamori abre correctamente pero la verify por
`SelectionItem.is_selected` falla (header ListItem sin cambio observable). En TE-06
el agente verifica compose con `spy_inspect` Value / `find_text` aunque `element-map.md`
ya documenta que CKEditor no refleja texto en ValuePattern.

**Solución:** Documentar cadenas de verify **ordenadas** en flujos TE-05 y TE-06 (skill producto),
sin depender de un solo pattern UIA:

- **TE-05 (chat abierto):** (1) título ventana contiene contacto → (2) `element_exists` header
  ListItem por name parcial → (3) `discover_control_interaction` compose encontrado →
  (4) `SelectionItem` solo como señal secundaria. WARN si (1–3) OK y (4) falla — no FAIL.
- **TE-06 (compose escrito):** (1) click/foco compose → (2) `type_into_element` con texto único →
  (3) verify vía `clipboard(read)` tras Ctrl+A **hasta** fix MCP `read_editable_text` →
  (4) prohibido `find_text` full-window si UIA no expone el texto. Limpiar con Ctrl+A Delete.

**Dónde:** `.cursor/skills/teams/flows/TE-05-chat-readonly.md`,
`.cursor/skills/teams/flows/TE-06-compose-no-send.md`, § Quirks en `teams/SKILL.md`.

## Contexto del turno

| Flujo | OBS/ACT | VERIFY | Estado |
|-------|---------|--------|--------|
| TE-04 | `set_element_value` search + `find_element` Awamori | screenshot dropdown | met (find_element 8389ms WARN) |
| TE-05 | `invoke_element` TreeItem `menurfp` (id rotó desde `menur2u`) | SelectionItem FAIL; header exists; compose discover | met WARN |
| TE-06 | type_into_element + type_text 41 chars | Value placeholder; find_text not found | partial |

TreeItem: buscar por `name` parcial «Awamori» + `role=TreeItem`, no cachear `automation_id`
entre sesiones (ya en element-map; flujos deben repetirlo explícitamente).

## Esfuerzo observado

TE-05 recuperado por señales alternativas; TE-06 bloqueado por verify incorrecta
(reintentos con 3 tools de escritura + OCR `find_text` prematuro).

## Texto propuesto

### TE-05 — Verify chat abierto (Electron)

```
VERIFY (cualquiera OK → met; todos FAIL → retry):
1. get_target_window.title contiene "Awamori" (o contacto esperado)
2. element_exists(name~="Awamori", role="ListItem") en header
3. discover_control_interaction(name="Escribe un mensaje", role="Edit")
4. SelectionItem en TreeItem — opcional; WARN si 1–3 OK y 4 falla
```

### TE-06 — Verify compose sin enviar

```
ACT: click compose → type_into_element(text=único, name="Escribe un mensaje")
VERIFY (hasta fix MCP contenteditable):
1. clipboard: focus compose → Ctrl+A → clipboard(read) contiene substring único
2. NO usar spy Value ni find_text como verify primario
CLEANUP: Ctrl+A → Delete → clipboard vacío o placeholder
```

### Quirk §4 (teams/SKILL.md)

Añadir ítem 7: «IDs UUID y TreeItem rotan — localizar por `name` + `role`; verify por
título ventana / header / clipboard cuando Value/SelectionItem es stale».

## Test de abstracción

Patrón L3: apps Electron con TreeItem + rich-text compose (Slack, Discord) se benefician
de verify multi-señal; el texto no nombra automation_id de Teams salvo como ejemplo en element-map.

## Verificación de duplicados

- `element-map.md` y `gaps/mcp-improvements.md` ya listan síntomas; flujos TE-05/TE-06 no tienen la cadena.
- No duplica `20260906_203600_contenteditable-compose-read-verify.md` (código MCP); esta skill es
  workaround/interino + routing correcto hasta que el código esté aplicado.
- `find_element` 8389ms: cubierto por backlog performance (`180000`, `notepad-list-elements-slow`);
  añadir nota TE-04: `find_element(role="TreeItem", name~="Awamori")` antes de barrido plano.

## Beneficios futuros

- Harness TE continúa con WARN honesto en lugar de FAIL falso o partial por verify incorrecta.
- Agente no escala a OCR (`find_text`) cuando clipboard-verify es suficiente.

## Criterio de aceptación

- [ ] TE-05 y TE-06 flows con bloques VERIFY copiables.
- [ ] Sin automation_id hardcodeado en pasos obligatorios (solo name/role).
- [ ] Referencia cruzada a propuesta código `203600` cuando `read_editable_text` exista.

---

## Ampliado — turno TE-07 met (2026-09-06 20:38 ART)

TE-07 **met** con envío único a Awamori; TE-06 **met** (promovido) vía screenshot compose.
Gaps residuales alineados con propuestas pendientes — no bloquean matriz pero exigen workaround.

| Flujo | Verify usada | Resultado |
|-------|--------------|-----------|
| TE-06 pre-send | screenshot `_14` (Value stale; find_text NOT FOUND) | **met** |
| TE-07 pre-send | screenshot compose (find_text compose fail) | OK workaround |
| TE-07 post-send | `find_text` + `find_element` historial | **OK** — UIA/OCR en burbuja |
| TE-07 act | `invoke_element` Enviar | 2368 ms success |

### TE-07 — Verify envío (asimetría compose vs historial)

```
PRE-SEND (compose — hasta fix MCP 203600):
1. screenshot(scope=window) contiene prefijo [AwdUI-MCP-TE]
2. NO find_text full-window como verify primario de compose (CKEditor stale)
3. clipboard Ctrl+A opcional si foco compose confirmado

ACT: invoke_element(name="Enviar (Ctrl+Enter)") o Enter — timing citado

POST-SEND (historial — UIA/OCR funciona):
1. find_text("[AwdUI-MCP-TE]") en ventana chat
2. find_element / read_element en panel mensajes
3. screenshot post-send hito (_16)
4. reuse: si burbuja harness <24h → met con nota reuse (message-safety.md)
```

**Routing:** no escalar OCR en compose cuando historial post-envío ya valida el flujo TE-07;
documentar la asimetría para evitar FAIL falso en pre-send por `find_text` prematuro.

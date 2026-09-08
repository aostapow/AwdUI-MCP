# Teams TE-05: TreeItem chat por name + verify header (no SelectionItem default)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-06 20:36:30 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | teams |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** Al abrir chat Awamori (TE-05), `automation_id=menur2u` quedó stale (rotó a `menurfp`).
`invoke_element` vía SelectionItem tardó ~3,8 s y el verify por defecto (`SelectionItem.is_selected`)
falló aunque el chat abrió; el agente recuperó con `element_exists` en header.

**Solución:** Documentar en flujo TE-05 y `element-map.md`:

1. Localizar chat en lista: `find_element(name="Awamori", role="TreeItem")` — **no** depender de
   `automation_id` rotativo (`menur2u` / `menurfp`).
2. Invocar con verify alternativo al header, no SelectionItem state:
   `invoke_element(name="…Awamori…", role="TreeItem", verify_name_contains="Awamori")`
   o `verify_automation_id` del header si estable (`listItemrbd` observado — marcar como hint rotativo).
3. Si verify SelectionItem falla pero header existe → considerar paso met con WARN; no reintentar invoke.

**Dónde:** `.cursor/skills/teams/flows/TE-05-chat-readonly.md`, `teams/element-map.md` § CHAT-LIST-ITEM,
`teams/protocol/agentic-execution.md` § Electron (verify sidebar lists).

## Texto propuesto

### Sidebar TreeItem (Electron) — abrir chat

| Paso | Act | Verify |
|------|-----|--------|
| Locate | `find_element(name="Awamori", role="TreeItem")` | count ≥ 1 |
| Open | `invoke_element(..., verify_name_contains="Awamori")` | header ListItem/name contiene Awamori |
| Fallback | `element_exists(name="Awamori", role="ListItem")` | no re-invoke si header OK |

**Evitar:** `verify` implícito SelectionItem-only tras invoke en listas Electron; IDs `menu*` rotan entre sesiones.

## Contexto del turno

Harness Teams TE-05 (MCP v0.4.0): búsqueda TE-04 OK; chat list `menur2u` stale;
`find_element` → `menurfp`; invoke SelectionItem 3836 ms verify FAIL; `element_exists` header OK → met WARN.

## Esfuerzo observado

~4 s en verify fallido + re-verificación manual header; riesgo de doble invoke si el agente interpreta FAIL como no abierto.

## Test de abstracción

Patrón aplica a sidebars Electron (Slack, Discord, VS Code activity bar) con TreeItem + SelectionItem
verify frágil — documentado en skill producto Teams, no en código MCP.

## Verificación de duplicados

- `element-map.md` ya anota rotación `menur2u→menurfp` y preferir name; falta **paso concreto** en TE-05
  y uso de `verify_name_contains` (parámetro ya existe en `invoke_element` — MCP_TOOLS_REFERENCE § invoke).
- No duplica propuesta compose (`20260906_203600_contenteditable-compose-read-verify.md`).

## Beneficios futuros

- TE-05 estable sin WARN; menos latencia por reintentos.
- Agente no bloquea TE-06 por falso negativo de SelectionItem verify.

## Criterio de aceptación

- [ ] TE-05 flow incluye params `verify_name_contains` en plantilla paso.
- [ ] element-map § CHAT-LIST-ITEM enlaza a verify header, no solo invoke.
- [ ] Sin hardcodear IDs rotativos como único localizador en el flujo.

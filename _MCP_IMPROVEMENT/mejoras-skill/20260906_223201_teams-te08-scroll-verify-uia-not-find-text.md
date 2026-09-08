# Teams TE-08: verificar scroll con UIA/tree_hash, no find_text full-window

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-06 22:32:01 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | teams-mcp-harness, teams |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** TE-08 live: `scroll_element` con `Scroll.Scroll` up/down **OK** (programático nativo).
Tras `scroll up`, `find_text` del ancla de historial devuelve **ausente**. El agente escala a OCR
full-window cuando el historial Teams WebView es virtualizado — viola jerarquía UIA-first y deja
`teams_perfect` en false por verify frágil post-scroll.

**Solución:** Documentar en `teams-mcp-harness/SKILL.md` (TE-08) y `teams/SKILL.md` (message pane)
cadena de verify **sin** `find_text` como primario tras scroll:

1. **Antes/después:** `get_tree_hash` o `ui_fingerprint` acotado al pane `message-pane-layout-a11y`
   (delta distinto de cero = scroll efectivo).
2. **Contenido:** `list_elements(role="ListItem"|"DataItem", automation_id=message-pane-layout-a11y
   o ancestro scrollable)` — leer `name`/`value` de burbujas visibles; no barrido full-window.
3. **`find_text`:** solo fallback documentado si UIA devuelve 0 items **y** scroll verify (hash) OK.
4. Tras scroll, `wait_for_condition` 300–500 ms antes de leer UIA (render WebView).
5. Gate `teams_perfect`: TE-08 cuenta como programático si `scroll_element.method` ∈ Scroll.* y verify
   usa hash o ListItem — no exigir `find_text` hit.

**Dónde:** `.cursor/skills/teams-mcp-harness/SKILL.md` § TE-08; `.cursor/skills/teams/SKILL.md`
§ historial chat; tabla gate en 213301 (fila scroll/verify).

## Texto propuesto

### TE-08 — Scroll historial (verify)

| Paso | Tool | Criterio |
|------|------|----------|
| 1 | `find_scrollable_ancestor` / `scroll_element` | `method` = `Scroll.Scroll` o `ScrollPattern` |
| 2 | `get_tree_hash` en message pane | delta ≠ 0 tras up/down |
| 3 | `list_elements(role=ListItem, max_depth=8)` en pane | ≥ 1 burbuja con texto legible |
| 4 (fallback) | `find_text` scope ventana | solo si paso 3 vacío y hash OK |

**Prohibido** FAIL TE-08 solo porque `find_text` no encuentra texto tras scroll up si el hash UIA
cambió y hay ListItems en el pane.

## Contexto del turno

- Scroll nativo Scroll.Scroll up/down OK (~800 ms).
- `find_text` ausente tras scroll up — verify harness incompleto.
- No re-envío TE-07 (correcto).
- `teams_perfect` false; matriz puede estar met con workaround OCR implícito.

## Verificación de duplicados

| Propuesta | Relación |
|-----------|----------|
| 213300 scroll keyboard before coords | Complementa — scroll ya nativo; este ítem es **verify post-scroll** |
| 213301 teams_perfect gate | Extender tabla TE-08: verify hash/ListItem, no find_text obligatorio |
| 204500 TE-09 return chat scroll | Paralelo TE-09; TE-08 es historial en chat activo |
| 203601 verify fallbacks compose | Distinto control (CKEditor vs historial) |

## Test de abstracción (L3)

Patrón «scroll programático + verify hash/UIA antes de OCR» aplicable a Electron chat/historial
sin IDs Teams en skill genérica.

## Esfuerzo observado

Agente no distingue scroll exitoso (UIA) de verify fallido (OCR); riesgo de reintentos find_text
lentos o falso negativo en gate calidad MCP.

## Criterio de aceptación

- [ ] Sección TE-08 en `teams-mcp-harness/SKILL.md` con tabla verify arriba.
- [ ] `teams/SKILL.md` referencia message pane + virtualización.
- [ ] Gate 213301 actualizado: TE-08 verify ≠ `find_text` obligatorio.
- [ ] Sin rutas `_MCP_IMPROVEMENT/` en texto skill.
- [ ] Alineado con `awdui-mission.mdc` jerarquía UIA > OCR.

## Beneficios futuros

- TE-08 repetible sin OCR full-window post-scroll.
- Evaluación honesta MCP: scroll programático + verify UIA = nivel 3 OK.
- Reduce falsos FAIL y tiempo OCR 5–10 s en historial virtualizado.

# read_element / type_into_element: lectura y verify en contenteditable (CKEditor)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-06 20:36:00 |
| **Usuario sesión** | ariel.ostapow |
| **Tipo de gap** | tool_gap |
| **Nivel** | L4 |
| **Versión MCP** | v0.4.0 (check_version: up to date) |

## Resumen

**Problema:** En campos `Edit` de apps Chromium/Electron (p. ej. compose de Teams con CKEditor),
`set_element_value` y `type_into_element` reportan éxito (`ValuePattern` o `click+type`) pero
`read_element` / `spy_inspect` siguen devolviendo el placeholder (`"Escribe un mensaje\n"`).
El agente no puede verificar TE-06 ni preparar TE-07 de forma programática.

**Solución:** Cascada genérica de lectura de texto editable en `do_read_element` y helper compartido
`read_editable_text(raw)`:

1. `ValuePattern.CurrentValue` (actual)
2. `TextPattern` / `DocumentRange` si soportado
3. `LegacyIAccessible.CurrentValue` / `CurrentName` vía `uia_text.get_item_text`
4. **Fallback contenteditable:** foco en el nodo → `Ctrl+A` → `clipboard(read)` → restaurar selección
   (solo si Value sigue siendo placeholder conocido o vacío tras `type_into_element`)

En `do_type_into_element`, parámetro opcional `verify: bool = false`: tras escribir, invocar la cascada;
si el texto esperado no aparece, devolver `success: false` con `verify_method` y `read_value` observado.

**Dónde:** `mcp-servers/awdui-server/detection/uia_text.py`, `tools/element_read_tools.py`
(`do_read_element`), `tools/ui_automation.py` (`do_type_into_element`).

## Contexto del turno

Harness Teams TE-06 (MCP v0.4.0):

| Paso | Tool | Resultado |
|------|------|-----------|
| Compose locate | `discover_control_interaction` | `set_element_value` high; patterns Value + LegacyIAccessible |
| Act 1 | `set_element_value` 41 chars | success — sin reflejo en Value |
| Act 2 | `type_into_element` 41 chars | success `click+type` |
| Act 3 | `type_text` 41 chars | success |
| Verify | `spy_inspect` Value | `"Escribe un mensaje\n"` (placeholder) |
| Verify | `find_text` `[AwdUI-MCP-TE]` | not found |
| Cleanup | Ctrl+A Delete | partial |

Target: `Chat | Awamori, Nicolas | Microsoft Teams` hwnd=132488.

## Esfuerzo observado

Múltiples intentos de escritura (3 tools) sin verify UIA confiable; TE-06 queda `partial`;
bloquea TE-07 (envío con verify previo obligatorio en harness).

## Cambio propuesto

```python
# detection/uia_text.py
def read_editable_text(raw, *, allow_clipboard: bool = False) -> dict:
    """Cascade Value → Text → LegacyIAccessible → optional clipboard."""
    ...

# tools/element_read_tools.py — do_read_element
text_result = read_editable_text(raw_elem, allow_clipboard=True)
props["text_content"] = text_result.get("text", "")
props["text_source"] = text_result.get("method")  # Value|Text|LegacyIAccessible|clipboard

# tools/ui_automation.py — do_type_into_element
def do_type_into_element(..., verify: bool = False, verify_timeout_ms: int = 500):
    ...
    if verify:
        read = read_editable_text(elem, allow_clipboard=True)
        if text not in (read.get("text") or ""):
            return {"success": False, "error": "verify_failed", "read": read, ...}
```

Documentar en `docs/MCP_TOOLS_REFERENCE.md` § `read_element` y `type_into_element`:
«En contenteditable Chromium, Value puede ser placeholder; usar `text_content` / verify con clipboard».

## Test de abstracción

Aplica a cualquier `Edit`/`Document` en Electron, WebView2, Slack, Notion desktop — no solo Teams.
No hardcodear «Teams» ni «CKEditor» en lógica; detectar por: Value == name placeholder, o
`framework in (electron, chromium_embedded)` + rol Edit sin cambio de Value post-type.

## Verificación de duplicados

- No hay propuesta abierta para contenteditable / CKEditor / clipboard-verify compose.
- Relacionado (no duplica): `combo-typeahead-fallback-verify` (WinForms combo, distinto control).
- Skill Teams `gaps/mcp-improvements.md` ya lista el síntoma; esta propuesta es fix MCP genérico.

## Beneficios futuros

- TE-06/TE-07 harness con verify programático sin OCR.
- Patrón reutilizable para otros campos rich-text en apps Chromium embebidas.
- Reduce falsos positivos de `type_into_element` success sin efecto real.

## Criterio de aceptación

- [ ] `tests/test_read_editable_text.py`: mock Edit con Value=placeholder y clipboard con texto real.
- [ ] `tests/test_type_into_element_verify.py`: verify=true falla si Value stale y clipboard vacío.
- [ ] Integración harness: TE-06 compose 41 chars → `read_element.text_content` contiene prefijo.
- [ ] `docs/MCP_TOOLS_REFERENCE.md` actualizado.
- [ ] Sin referencias a automation_id de Teams en código del servidor.

---

## Ampliado — turno TE-04..TE-06 (2026-09-06 20:35 ART)

Confirmación en vivo del bloqueo TE-07:

| TE | Resultado | Evidencia |
|----|-----------|-----------|
| TE-04 | met | `set_element_value` search + dropdown screenshot OK |
| TE-05 | met WARN | `menur2u` stale → `menurfp`; invoke 3838 ms, SelectionItem verify FAIL, header OK |
| TE-06 | partial | 3× write success; Value placeholder; `find_text` NOT FOUND; cleanup partial |

**Prioridad P1** para harness: implementar cascada antes de TE-07. `find_text` no sustituye verify
compose — texto CKEditor no aparece en OCR de ventana con Value stale.

---

## Ampliado — turno TE-07 met (2026-09-06 20:38 ART)

TE-07 completó envío único a Nicolás Awamori con prefijo `[AwdUI-MCP-TE]` pese al gap compose.
TE-06 promovido a **met** vía screenshot pre-send (workaround hasta cascada MCP).

| Paso | Tool | Resultado |
|------|------|-----------|
| Pre-send compose | `find_text` `[AwdUI-MCP-TE]` | **NOT FOUND** (OCR compose stale) |
| Pre-send compose | `screenshot` `_14` | OK — texto visible en imagen |
| Act envío | `invoke_element` Enviar | success **2368 ms** |
| Post-send historial | `find_text` + `find_element` | **OK** — burbuja con prefijo |
| Post-send hito | `screenshot` `_16` | OK |

**Asimetría confirmada:** compose CKEditor no expone texto a Value ni OCR pre-send; panel
historial **sí** es legible vía `find_text`/`find_element` post-envío. El fix `read_editable_text`
sigue siendo P1 para TE-06 y verify pre-send TE-07; post-send no requiere cambio MCP adicional.

**Refuerza criterio:** `type_into_element(verify=true)` debe usar cascada clipboard, no asumir
éxito por `find_text` en ventana completa antes de Enviar.

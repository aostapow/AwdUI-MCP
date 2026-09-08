# Post-act verify: cierre de modal Win32 (#32770)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | aplicada |
| **Fecha** | 2026-09-06 17:45:00 |
| **Tool afectada** | `invoke_element`, `click_element`, `send_keys` |
| **Módulo código** | `tools/action_timing.py`, `tools/ui_automation.py`, `tools/target_window.py` |
| **Tipo de gap** | tool_gap |
| **Nivel** | L4 |
| **Versión MCP** | 0.2.1 (turno); sin `updateAvailable` consultado en advisor |

## Resumen

**Problema:** Tras `invoke_element` / `click_element` / `send_keys` en botones de cierre de diálogos Win32
(`Cancelar`, `No guardar`, `Escape`), el MCP reporta éxito (`verified: true` o sin flag de fallo) aunque
`list_windows` sigue mostrando el modal `#32770` (ej. `Buscar`, `Guardar como`). El agente debe hacer
una tool extra solo para confirmar cierre — viola protocolo «una tool por paso» y causó recovery L1 en
NP-10/11/06 (Notepad harness 2026-09-06).

**Solución:** Parámetro opcional `verify_modal_dismissed: bool` (default `false` para compatibilidad).
Cuando el target es ventana `#32770` o rol `Dialog`, tras la acción poll `list_windows` filtrado por
PID/HWND del target y comprobar ausencia del título modal. Respuesta enriquecida:
`modal_dismissed: true|false`, `modal_still_open: "<título>"`, `verify_ms`. Si sigue abierto →
`verified: false` + hint «usar list_windows o recovery L1».

**Dónde:** `run_post_act_verify` + helpers en `target_window.py`; documentar en `MCP_TOOLS_REFERENCE.md`.

## Contexto del turno

- Usuario: `ariel.ostapow`
- Pedido: harness Notepad protocolo estricto NP-10, NP-06, NP-11
- NP-10 met: Ctrl+B → modal Buscar #32770; cierre verificado solo con `list_windows` (skill NP-10 paso 6)
- NP-06 met: Alt+F4 → invoke «No guardar»; L3 recovery tras estado sucio
- NP-11 met: Reemplazar id=23, Reemplazar todo; verify status bar id=1025 vía `read_element`
- Recovery L1: modal `Guardar como` stale bloqueó teclado antes de baseline
- Skills leídas: `awdui-flow-exploration`, `notepad/SKILL.md`, `protocol/agentic-execution.md`, `protocol/recovery.md`

## Esfuerzo observado

- Paso verify cierre modal = tool MCP adicional obligatoria (`list_windows`) tras cada dismiss
- Anti-patrón ya documentado en `agentic-execution.md` y `NP-10-find.md` pero sin señal MCP
- Recovery L1 por modal stale añadió 2–3 tools extra al inicio de flujos

## Cambio propuesto (pseudodiff)

```python
# action_timing.py
def run_post_act_verify(
    *,
    window_title: Optional[str] = None,
    verify_modal_dismissed: bool = False,
    modal_title: Optional[str] = None,  # default: window_title del act
    parent_pid: Optional[int] = None,
    timeout_ms: int = 5000,
    ...
) -> dict[str, Any]:
    ...
    if verify_modal_dismissed and modal_title:
        from tools.windows import list_modal_windows_for_pid
        for _ in poll:
            open_modals = list_modal_windows_for_pid(parent_pid, class_name="#32770")
            if not any(m["title"] == modal_title for m in open_modals):
                return {"verified": True, "modal_dismissed": True, "verify_ms": ...}
        return {
            "verified": False,
            "modal_dismissed": False,
            "modal_still_open": modal_title,
            "verify_error": "modal still in list_windows",
            "hint": "recovery L1: focus_window + Cancelar; do not trust act-only success",
        }
```

```python
# ui_automation.py — do_invoke_element / do_click_element
if verify_modal_dismissed or _is_dialog_target(window_title, element):
    attach_modal_verify(result, window_title=window_title, timeout_ms=verify_timeout_ms)
```

**Relacionado (performance):** `invoke_element` verify en MenuItem/modales Notepad 10–17s
(`notepad/gaps/mcp-improvements.md`) — usar `verify_timeout_ms` separado del act (default 1500ms
para modal dismiss; no poll `verify_name_contains` en MenuItem).

## Test de abstracción

Cross-app: cualquier Win32/WinForms con `#32770` — Guardar como, Buscar, Confirmar guardar,
Imprimir, AST lookup. No depende de automation_ids de Notepad.

## Verificación de duplicados

- **Relacionado, distinto:** `aceptadas/mejoras-codigo/20260906_171700_get-all-values-modal-scope-role-walk.md`
  (scope leak al leer valores; no verify post-dismiss).
- **Relacionado, distinto:** `aceptadas/mejoras-codigo/20260905_211200_post-act-verify-display-target.md`
  (verify target equivocado en Calculadora; no modales).
- **No duplica:** `2026-09-06-notepad-list-elements-slow.md` (performance list walk).
- Skill `notepad/protocol/agentic-execution.md` documenta workaround agente; esta propuesta cierra
  el gap MCP que obliga al workaround.

## Criterio de aceptación

- [ ] `tests/test_modal_dismiss_verify.py`: mock `list_windows` con modal presente/ausente →
      `verified` coherente con `modal_dismissed`.
- [ ] Live Notepad: `click_element(Cancelar, window_title="Buscar", verify_modal_dismissed=true)` →
      `modal_dismissed: true` sin `list_windows` manual.
- [ ] Live Notepad: `send_keys escape` con modal abierto → `modal_dismissed: false` si sigue en
      `list_windows`.
- [ ] Documentado en `MCP_TOOLS_REFERENCE.md` (`verify_modal_dismissed`, `verify_timeout_ms`).
- [ ] Default `false` — sin breaking change en tools existentes.

## Beneficios futuros

- Menos tools por flujo modal (elimina verify manual `list_windows` en NP-10/18/recovery).
- Señal estructurada para recovery L1 automático en agente (`modal_still_open` → hint).
- Alinea post-act verify con protocolo agentic «Act + Verify en una tool».


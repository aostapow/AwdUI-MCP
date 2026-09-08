# Win32 modal Edit: fallback HWND cuando UIA no expone el campo

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-06 17:52:00 |
| **Usuario sesión** | ariel.ostapow |
| **Tool afectada** | set_element_value, fill_form, get_all_values (lectura simétrica) |
| **Tipo de gap** | deteccion |
| **Nivel** | L4 |
| **Versión MCP** | 0.2.1 |

## Resumen

**Problema:** En el diálogo **Ir a la línea** de Notepad (`#32770`, título `Ir a la línea`), el modal abre
(id=24) y los botones son visibles en UIA, pero el **Edit de número de línea no aparece** en
`list_elements` / `get_all_values`. `set_element_value(name="Número de línea:")` falla; tras
`invoke_element(Ir a)` el cursor permanece en **Línea 1** (StatusBar).

**Solución:** Cuando el scope resuelve un modal `#32770` y UIA no encuentra `Edit`/`Document` con
ValuePattern, enumerar hijos Win32 (`EnumChildWindows`) por clase `Edit`, mapear a HWND y escribir
vía `WM_SETTEXT` / `SendMessage` o `set_value_hwnd` interno. Exponer los campos descubiertos también
en `get_all_values` con metadata `{ source: "win32_edit_hwnd" }`.

**Dónde:** `detection/form_read.py`, `tools/ui_automation.py` (`do_set_element_value`),
`tools/window_scope.py` (reutilizar modal HWND ya resuelto), nuevo helper
`detection/win32_modal_edits.py`.

## Contexto del turno

- Pedido: harness Notepad NP-12..NP-20, protocolo agentic + recovery.
- **NP-15 met:** scroll 100 líneas, StatusBar L1→83.
- **NP-17 met:** `get_all_values` sin leak de Calculadora (fix scope modal 171700 operativo).
- **NP-20 met:** page setup + imprimir.
- **NP-12 partial:** Ctrl+G / menú → modal `#32770` abre; campo línea ausente en UIA; cursor L1.
- Recovery: L1 modal Guardar como stale, L3 `close_app`+`launch_app` — protocolo OK.
- Skills: `awdui-flow-exploration`, `notepad`, `protocol/agentic-execution`, `protocol/recovery`.
- MCP: 0.2.1.

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| Edit Ir a línea no en árbol UIA | deteccion | L4 | Sí (este archivo) |
| NP-15/17/20 exitosos | — | — | No |
| Recovery L1/L3 Guardar como | entorno | L1 | No — skill recovery |
| list_elements lento Notepad | performance | L3 | Backlog `2026-09-06-notepad-list-elements-slow.md` |

UIA parcial en Win32 `#32770` es patrón conocido (Buscar/Reemplazar a veces expone Edit; Ir a línea
no). El agente no debe escalar a OCR/coords: el control Win32 existe pero el walk UIA lo omite.

## Cambio propuesto

### 1. Helper `enumerate_modal_edits(modal_hwnd) -> list[dict]`

```python
# detection/win32_modal_edits.py
def enumerate_modal_edits(modal_hwnd: int) -> list[dict[str, Any]]:
    """EnumChildWindows on #32770; return Edit class children with hwnd, text, rect."""
```

Filtrar clase `Edit` (case-insensitive). Opcional: leer label estático hermano (`Static`) para
`name` cuando UIA no lo provee.

### 2. Fallback en `do_set_element_value`

Tras fallo UIA (`element not found`) y `window_handle` apunta a modal `#32770`:

1. `edits = enumerate_modal_edits(hwnd)`
2. Match por `name` (substring, ej. `línea`), `automation_id`, o `index`
3. Escribir con Win32 API; retornar `{ success, method: "win32_edit_hwnd", hwnd, ... }`

### 3. Lectura simétrica en `get_all_values`

Si walk UIA devuelve 0 `Edit` en modal scoped y `modal_class == "#32770"`, merge edits Win32 al
payload (misma dedupe key que Document+Edit).

### 4. Parámetro opcional (documentación)

`set_element_value(..., win32_edit_fallback=True)` default **true** cuando scope es modal owned.

## Test de abstracción (L4)

Aplica a cualquier app Win32/WinForms con `#32770` cuyo Edit no esté en UIA: diálogos legacy,
utilidades del sistema, algunos modales COBIS Win32. No depende de automation_ids de Notepad.

## Verificación de duplicados

- **No duplica:** `20260906_171700_get-all-values-modal-scope-role-walk.md` (scope modal + leak;
  este gap es **controles ocultos a UIA** dentro del modal ya scoped).
- **No duplica:** `20260906_174500_post-act-verify-modal-dismissed.md` (verify cierre modal).
- **Relacionado skill:** `notepad/flows/NP-12-goto-line.md` pending — actualizar tras implementar.

## Esfuerzo observado

Turno parcial en NP-12: modal abierto, múltiples intentos UIA sin campo; recovery L1 por modal
stale previo. Bloquea `notepad_perfect` (18/20).

## Evidencia resolución alternativa (2026-09-06 17:55 ART)

**NP-12 met** sin HWND fallback: `spy_tree(mode="raw", max_depth=8, window_title="Ir a la línea")`
expone `Edit id=258`; `set_element_value(258, "5")` + invoke Ir a → StatusBar `Línea 5`.
Skill `notepad/flows/NP-12-goto-line.md` documenta el routing.

**Prioridad revisada:** implementar auto-intento `include_offscreen` / `spy_tree raw` en
`set_element_value` antes del fallback Win32; HWND sigue útil cuando raw tampoco expone el Edit.

## Criterio de aceptación

- [ ] `tests/test_win32_modal_edit_fallback.py`: mock EnumChildWindows → set value OK.
- [ ] Live Notepad NP-12: `set_element_value(name="Número de línea:", value="5",
  window_title="Ir a la línea")` → StatusBar `Línea 5`.
- [ ] `get_all_values` con modal Ir a línea abierto incluye al menos un Edit (UIA o win32 fallback).
- [ ] Sin regresión: NP-17 scope modal Imprimir sigue sin leak editor padre.
- [ ] Documentado en `docs/MCP_TOOLS_REFERENCE.md` (`set_element_value`, `get_all_values`).

## Beneficios futuros

- Cierra NP-12 sin OCR ni coords.
- Patrón reutilizable para modales Win32 opacos (complementa scope modal 171700).
- Reduce dependencia de atajos teclado frágiles cuando el foco no cae en el Edit.

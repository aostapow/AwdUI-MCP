# get_all_values: scope modal foreground + walk filtrado por roles

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | aplicada |
| **Fecha** | 2026-09-06 17:17:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | detection/form_read.py, tools/form_tools.py, tools/window_scope.py, detection/orchestrator.py |
| **Tool afectada** | get_all_values, fill_form (scope simétrico) |
| **Tipo de gap** | deteccion |
| **Nivel** | L4 |
| **Impacto** | alto |
| **MCP versión** | v0.4.0 |

## Resumen

**Problema:** Tras abrir el diálogo **Imprimir** en Notepad (`#32770`), `get_all_values` con
`set_target_window("Bloc de notas")` devolvió **12 campos del diálogo mezclados con controles
del editor padre** (scope leak). La tool llama `do_list_elements` sin `resolve_scoped_window`,
sin `window_handle`, y sin detectar el modal foreground del mismo PID. Además, el walk usa
`max_depth=12` sobre **todo** el árbol y filtra roles editables solo en Python — en ventana
principal Notepad (24 nodos) tardó **3794 ms** (⚠ SLOW) para un inventario mínimo.

**Solución:**

1. **Auto-scope modal:** Si hay ventana foreground `#32770` (o `Dialog` UIA) owned por el PID del
   target, y el caller no pasó `window_handle` explícito, resolver HWND del modal y acotar
   `list_elements` a ese subárbol. Metadata: `{ scope: "foreground_modal", modal_title, hwnd }`.
2. **Parámetro explícito** `scope_mode`: `auto` (default), `target`, `foreground`, `handle`.
3. **Walk filtrado:** Internamente invocar walk con filtro de roles (`Edit`, `ComboBox`,
   `CheckBox`, `Document`, `Spinner`, `RadioButton`) o múltiples passes con `role=` en lugar de
   barrido completo + filtro post-hoc.
4. **fill_form** simétrico: usar el mismo resolver de scope antes de `set_element_value` batch.
5. Documentar en `MCP_TOOLS_REFERENCE.md`: con modal abierto, preferir
   `get_all_values(window_title="Imprimir")` o dejar `scope_mode=auto`.

**Dónde:** `form_read.get_all_values`, `form_tools.do_get_all_values` / `do_fill_form`,
`window_scope.py` (helper `resolve_foreground_owned_modal(pid)`), `docs/MCP_TOOLS_REFERENCE.md`.

## Contexto del turno

- Harness Notepad max cobertura MCP: `launch_app` OK, `detect_framework` win32.
- `set_element_value` editor id=15 OK; `get_all_values` inicial devolvió **name-as-value** en
  Document (bug `_read_value` — corregido en turno con tests).
- `fill_form` Guardar como OK; `invoke_element` menús OK.
- `click_element` **Edición** FAIL tras menú Archivo abierto (ver propuesta skill menubar).
- Post-fix `_read_value`: `get_all_values` con modal **Imprimir** abierto → 12 campos con leak
  del editor Notepad en el mismo payload.
- Skills: `awdui-flow-exploration`, `notepad` (nueva), `awdui-mcp-objective`.

## Cambio propuesto (pseudodiff)

```python
# window_scope.py
def resolve_foreground_owned_modal(parent_pid: int) -> Optional[dict]:
    """Return foreground dialog owned by parent_pid (#32770 / Dialog role)."""
    ...

# form_read.py
def get_all_values(
    window_title: Optional[str] = None,
    window_handle: Optional[int] = None,
    max_depth: int = 12,
    scope_mode: str = "auto",
) -> dict[str, Any]:
    from tools.window_scope import resolve_foreground_owned_modal
    from tools.params import resolve_scoped_window
    wt, hwnd, _ = resolve_scoped_window("", window_title or "", "", window_handle or 0)
    if scope_mode == "auto" and not hwnd and wt:
        modal = resolve_foreground_owned_modal(pid_from_target(wt))
        if modal:
            wt, hwnd = modal["title"], modal["hwnd"]
    listing = do_list_elements(
        window_title=wt,
        window_handle=hwnd,
        max_depth=max_depth,
        roles=_EDITABLE_ROLES,  # nuevo param interno o multi-role walk
    )
    ...
```

```python
# orchestrator / uia_backend — roles filter at walk time
def list_elements(..., roles: Optional[Sequence[str]] = None):
    if roles:
        # OR-combine role filter during walk; skip unrelated subtrees early
```

## Verificación de duplicados

- **Extiende** tema `window-scope` (`124501` aceptada, `212400` spy_tree residual,
  `210301` within_automation_id): este gap es **form read/fill** sin HWND explícito cuando hay
  modal owned foreground — no duplica `within_automation_id` (ancestro conocido) ni `spy_tree`.
- **Distinto** del fix `_read_value` name-as-value (aplicado en turno con
  `test_get_all_values_document_*`).
- **Distinto** de `invalidate_tree_cache` en `set_element_value` (aplicado en turno).

## Test de abstracción

Cross-app: cualquier Win32/WinForms con `#32770` (Guardar como, Imprimir, Buscar, Confirmar),
AST lookup modals, file pickers. No específico de Notepad.

## Criterio de aceptación

- [ ] `tests/test_form_read_modal_scope.py`: mock foreground modal mismo PID → solo campos del diálogo.
- [ ] `tests/test_form_read_role_walk.py`: walk con roles no invoca filtro post-hoc sobre Button/MenuItem.
- [ ] Live Notepad: `get_all_values` con Imprimir abierto → `scope=foreground_modal`, sin key `15` (editor).
- [ ] Latencia `get_all_values` ventana principal Notepad < 1500 ms (24 nodos visibles).
- [ ] `MCP_TOOLS_REFERENCE.md`: `scope_mode`, modal auto-detect, ejemplo `window_title="Imprimir"`.

## Beneficios futuros

- Verify de formularios modales sin leak del padre (evita falsos positivos en harness).
- Menos latencia en `fill_form`/`get_all_values` en apps Win32 pequeñas.
- Alineación con `active-window.md` sub-flujo modal sin exigir HWND manual del agente.

## Esfuerzo observado

- Diagnóstico scope leak tras fix name-as-value; agente debió usar `window_title` del diálogo
  manualmente (documentado en skill notepad quirk #6) — MCP debería auto-acotar.
- `list_elements` 3794 ms para 24 elementos en ventana principal — overhead de walk completo.

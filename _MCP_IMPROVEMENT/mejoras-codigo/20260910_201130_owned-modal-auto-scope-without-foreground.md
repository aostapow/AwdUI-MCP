# scope_mode auto: modal #32770 owned único sin exigir foreground

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 20:11:30 |
| **MCP versión** | v0.4.0 (check_version: up to date) |
| **Tool afectada** | `invoke_element`, `click_element`, `find_element`, `list_elements`, `get_snapshot`, `get_all_values`, `fill_form` |
| **Módulo** | `tools/window_scope.py`, `tools/ui_automation.py` (`_resolve_click_invoke_scope`) |
| **Tipo de gap** | deteccion |
| **Nivel** | L4 |

## Resumen

**Problema:** Con `set_target_window` en Explorador de archivos y un diálogo `#32770` del **mismo PID**
abierto (F-22 «Configuración seguridad»), `invoke_element` / `click_element` con `scope_mode=auto`
(default) siguen buscando/actuando en la ventana padre. `find_element(Cancelar)` puede resolver en
árbol equivocado; `invoke_element` falla (~1829 ms) hasta `focus_window` en el título del modal y
reintento (~388 ms OK).

**Solución:** Tras fallar `resolve_foreground_owned_modal`, en modo `auto` usar fallback
`list_owned_dialogs(parent_pid)`: si hay **exactamente un** diálogo `#32770` visible owned, acotar
scope a su HWND/título (`scope: owned_modal`). Si hay varios, devolver metadata + hint
(`list_windows` / `window_title` explícito). Opcional: `ensure_modal_focus` solo para pointer, no
bloquear invoke UIA.

**Dónde:** `resolve_form_read_scope` / `resolve_action_scope` en `window_scope.py`;
respuesta enriquecida en act/find cuando scope cambia; `tests/test_form_read_modal_scope.py`;
`docs/MCP_TOOLS_REFERENCE.md` § `scope_mode`.

## Contexto del turno

- **Usuario:** ariel.ostapow · **Lab:** Escritorio Windows 2026-09-10 · **F-22 met** (14 met; cola ~84 flows).
- **discover-F-22:** `list_elements` **11571 ms** — walk mezcla Explorador + modal `#32770` con `scope_mode=auto` y target padre.
- Secuencia: Tab Compartir → invoke Seguridad avanzada → `list_windows` modal `#32770` →
  `find_element` Cancelar OK → `invoke_element` Cancel **fail** (target explorer) →
  `click_element` fail (foreground skip coords) → `focus_window` modal → `invoke_element` Cancel OK →
  modal dismissed.
- `improvements.jsonl`: «modal mismo PID explorer; auto scope mejorable» · `fix_in_cycle: not_attempted`.

## Análisis del gap

| Pregunta | Respuesta |
|----------|-----------|
| ¿Ejecución pura? | Parcial: `active-window.md` pide `window_title` del diálogo; el agente confió en `auto`. |
| ¿Detección MCP? | **Sí:** `auto` solo promueve modal si es **foreground** `#32770` (ver `resolve_foreground_owned_modal`). Modal abierto con padre aún foreground → scope padre. |
| ¿Cross-app? | Sí: Notepad Buscar/Imprimir, Explorador permisos, WinForms `#32770` mismo proceso. |

## Cambio propuesto

```python
# window_scope.py — dentro de resolve_form_read_scope, rama auto, tras modal FG None:

if modal is None and parent_pid is not None:
    owned = list_owned_dialogs(parent_pid=parent_pid)
    if len(owned) == 1:
        w = owned[0]
        return {
            "scope": "owned_modal",
            "window_title": w.get("title") or "",
            "window_handle": int(w.get("hwnd") or 0),
            "modal_class": w.get("class_name"),
            "parent_title": wt,
            "scope_note": "single owned #32770; foreground not required",
        }
    if len(owned) > 1:
        base["owned_dialogs"] = [
            {"title": d.get("title"), "hwnd": d.get("hwnd")} for d in owned
        ]
        base["hint"] = "multiple owned modals; pass window_title or window_handle"
```

En `do_invoke_element` / `do_click_element` / `do_list_elements` / `do_get_snapshot`, cuando
`scope_info["scope"] == "owned_modal"`, acotar HWND del modal y incluir en JSON `resolved_scope`
para trazabilidad lab (evita barridos 11+ s del árbol del Explorador con modal abierto).

Si invoke sigue fallando (InvokePattern en botón modal sin foco), enriquecer error con:
`hint: focus_window(<modal_title>) or window_handle=<hwnd>` — no sustituir el fallback owned.

## Test de abstracción

Aplica a cualquier app Win32/WinForms que abre `#32770` en el mismo proceso que el target MCP
(Explorador, Notepad, diálogos sistema). Distinto de Teams picker WebView2 (PID distinto — ya cubierto
por fallback `parent_pid=None` en 171700).

## Verificación duplicados

- **Extiende** `aceptadas/mejoras-codigo/20260906_171700_get-all-values-modal-scope-role-walk.md`
  (solo foreground modal) — **no duplica**; este gap es modal **no foreground**.
- Tema manifest `child-window` / `window-scope`: consolidar al implementar ambos en un solo PR
  `window_scope.py`.

## Esfuerzo observado

- 2 tools fallidas + 1 `focus_window` manual + reintento invoke antes de verify F-22.
- Flujo `met` con workaround; nivel harness OK, MCP operativo **no** (workaround obligatorio).

## Criterio de aceptación

- [ ] `tests/test_form_read_modal_scope.py`: mock `list_owned_dialogs` retorna 1 modal, FG no es `#32770` → scope `owned_modal`.
- [ ] `tests/test_form_read_modal_scope.py`: 2 modals owned → no auto-pick; hint en respuesta.
- [ ] Replay F-22 (o Notepad Buscar + Cancel): `invoke_element(name="Cancelar", scope_mode=auto)` sin `focus_window` previo → success & modal dismissed.
- [ ] Sin regresión: cuando FG ya es modal owned, sigue `foreground_modal` (171700).
- [ ] `docs/MCP_TOOLS_REFERENCE.md`: documentar fallback `owned_modal` en `scope_mode=auto`.

## Beneficios futuros

- Elimina workaround `focus_window` antes de Cancel en modales mismo-PID (F-22, recovery L1 Notepad).
- Alinea comportamiento documentado de `scope_mode=auto` con expectativa del agente tras `list_windows` modal visible.

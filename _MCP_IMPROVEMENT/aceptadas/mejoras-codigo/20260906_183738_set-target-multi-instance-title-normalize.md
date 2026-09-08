# set_target_window: multi-instancia + título dirty (*)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | aplicada |
| **Fecha** | 2026-09-06 18:37:38 |
| **Usuario sesión** | ariel.ostapow |
| **Tool afectada** | `set_target_window`, `focus_window`, `find_matching_window`, `resolve_scoped_window` |
| **Módulo** | `tools/windows.py`, `tools/target_window.py`, `tools/window_scope.py`, `tools/params.py` |
| **Tipo de gap** | deteccion |
| **Nivel** | L4 |
| **MCP versión** | v0.4.0 |

## Resumen

**Problema:** Con **dos o más** ventanas del mismo proceso (NP-26: Archivo → Nueva ventana id=8),
`set_target_window("Bloc de notas")` resuelve por substring y `_best_window_candidate` elige una
por heurística (área/posición), no la ventana deseada. Tras editar, el título dirty Win32 agrega
prefijo `*` (ej. `*Sin título: Bloc de notas` vs `Sin título: Bloc de notas`); alternar target
entre A y B exige títulos exactos distintos y re-set cuando A pasa a dirty — fricción dual
`set_target` con/sin asterisco.

**Solución:** (1) Normalizar matching: comparar títulos ignorando `*` inicial y espacios. (2) Si
≥2 candidatos del mismo `process_name` matchean el hint, **no** elegir silenciosamente: retornar
`ambiguous: true` + lista `{hwnd, title, pid}` y hint «usar título exacto de list_windows o
window_handle». (3) Extender `set_target_window` con `window_handle: int = 0` (como
`focus_window` / `find_element`) para scope estable multi-instancia. (4) Opcional
`disambiguate: "foreground" | "last_set" | "error"` (default `error` cuando hay empate).

**Dónde:** `find_matching_window`, `_best_window_candidate`, `set_target` session store (guardar
hwnd+title), `docs/MCP_TOOLS_REFERENCE.md` § set_target_window / NP multi-window.

## Contexto del turno

- Usuario: `ariel.ostapow`
- Pedido: continuar harness Notepad agentico NP-26 y NP-27
- **NP-26 met:** Nueva ventana id=8, 2 PIDs scope aislado, `get_all_values` target OK,
  Alt+F4 + «No guardar» cierra ventana B
- **NP-27 met:** Hora y fecha id=26 (nombre ES «Hora y fecha», no «Fecha y hora»), insert
  `18:36 6/9/2026`, 2 líneas; Deshacer menú undo step1 verified 2→1 línea
- Fricción estructural reportada: dual `set_target_window` por título con/sin `*`
- Skills leídas: `awdui-mcp-objective`, `notepad`
- MCP v0.4.0

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| Multi-instancia + asterisco dirty en set_target | deteccion | L4 | Sí (este archivo) |
| invoke_element verify slow/fail MenuItem | performance / tool_gap | L4 | Backlog `183322`, `174500` — ampliar |
| ctrl+z undo necesita clic editor entre pasos | routing_tool / entorno | L3 | Backlog `183323` — ampliar |
| Nombre menú «Hora y fecha» vs doc «Fecha y hora» | sintoma_app / ejecucion | L1 | `element-map.md` ya correcto; NP-27 met |

Código actual (`windows.py` ~79–98): substring `title_lower in w["title"].lower()` — ambas
ventanas «Sin título: Bloc de notas» matchean; `_best_window_candidate` desempata por área sin
señal de instancia. Tras dirty, `*Sin título...` **no** matchea hint `Sin título` si el agente
pasó título sin asterisco (o viceversa).

## Cambio propuesto (pseudodiff)

```python
# windows.py
def _normalize_window_title_for_match(title: str) -> str:
    t = (title or "").strip()
    while t.startswith("*"):
        t = t[1:].lstrip()
    return t.lower()

def find_matching_window(title: str, windows: list[dict]) -> dict:
    title_lower = _normalize_window_title_for_match(title)
    candidates = [
        w for w in windows
        if title_lower in _normalize_window_title_for_match(w.get("title") or "")
    ]
    if len(candidates) > 1 and _same_process(candidates):
        return {
            "window": None,
            "ambiguous": True,
            "candidates": [
                {"hwnd": w["hwnd"], "title": w["title"], "pid": w.get("pid")}
                for w in candidates
            ],
            "hint": "Multiple windows match; pass exact title from list_windows or window_handle",
        }
    ...
```

```python
# target_window.py — set_target_window
def set_target_window(
    title: str = "",
    window_title: str = "",
    window_handle: int = 0,
    focus_policy: str = "",
) -> str:
    if window_handle:
        win = resolve_window_by_hwnd(window_handle)
        set_target(win["title"], hwnd=window_handle)
    else:
        match = find_matching_window(resolved, do_list_windows())
        if match.get("ambiguous"):
            return json.dumps(match)  # or structured error string
        set_target(match["window"]["title"], hwnd=match["window"]["hwnd"])
```

## Test de abstracción (L4)

Cross-app: Notepad multi-ventana, WordPad, Bloc de notas + documentos dirty `*`, cualquier Win32
con varias top-level del mismo exe (Chrome perfil múltiple parcial — HWND sigue siendo clave).
No depende de automation_ids de Notepad.

## Verificación de duplicados

- **Consolidar tema** `window-scope` con `20260905_212400_spy-tree-target-window-scope.md`
  (spy scoped) y `20260906_180000_find-element-target-scope-false-positive.md` (cross-HWND false
  positive) — este gap es **elección incorrecta entre ventanas legítimas del mismo proceso**, no
  leak a otra app ni spy sin scope.
- **No duplica** `20260906_171700_get-all-values-modal-scope-role-walk.md` (modal auto-scope).
- Skill NP-26 ya documenta «título exacto segunda ventana» — el MCP debe soportarlo sin fricción
  asterisco + ambigüedad silenciosa.

## Esfuerzo observado

NP-26: pasos extra `list_windows` + `set_target` alternando títulos exactos (con/sin `*`) al
volver ventana A tras editar B; riesgo de scope leak si heurística elige ventana grande/equivocada.

## Criterio de aceptación

- [ ] `tests/test_window_title_normalize.py`: `*Sin título: Bloc de notas` matchea hint
  `Sin título: Bloc de notas`.
- [ ] `tests/test_set_target_ambiguous.py`: 2 notepad.exe + hint genérico → `ambiguous: true` con
  2 candidatos, sin set silencioso.
- [ ] Live NP-26: `set_target_window(window_handle=<hwnd B>)` estable; volver a A tras dirty sin
  re-list manual de asterisco.
- [ ] `set_target_window(window_handle=…)` documentado en `MCP_TOOLS_REFERENCE.md`.
- [ ] Sin regresión: una sola ventana Notepad sigue resolviendo con `Bloc de notas`.

## Beneficios futuros

- NP-26..NP-30 y flujos multi-documento Win32 sin alternar títulos frágiles por dirty flag.
- Menos scope leak accidental entre instancias del mismo proceso.
- Patrón reutilizable para MDI/multi-window sin hardcode de producto en el servidor.

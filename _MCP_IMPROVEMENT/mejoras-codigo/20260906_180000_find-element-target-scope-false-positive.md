# find_element: rechazar matches fuera del client rect del target

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-06 18:00:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | detection/orchestrator.py, tools/ui_automation.py, detection/element_scope.py |
| **Tool afectada** | find_element, wait_for_element, smart_find (cascada) |
| **Tipo de gap** | deteccion |
| **Nivel** | L4 |
| **Versión MCP** | 0.2.1 |

## Resumen

**Problema:** Con `set_target_window("Calculadora")` y Cursor enfocado, `find_element(automation_id=num7Button)`
tarda **4698ms** y devuelve `id=4101` (Edit «Cuadro de búsqueda» de Cursor), no el botón Siete.
`wait_for_element` reporta OK con el match erróneo. Contamina verificación y suma a criterio
**eficiencia fail** (`find_element` slow + wrong).

**Solución:** Tras resolver matches UIA, filtrar por **client rect** del HWND target
(`target_window` / `resolve_window_handle`). Descartar elementos cuyo bbox no intersecte el rect
(score 0). Si `automation_id` solicitado no coincide post-filtro, continuar búsqueda spy/repo
antes de retornar primer match global. Metadata: `rejected_foreign`, `target_hwnd`.

**Dónde:** `element_scope.filter_elements_to_scope` (reutilizar/ampliar), `orchestrator.find_elements`,
`do_find_element`; tests `tests/test_find_element_target_scope.py`.

## Contexto del turno

- Auditoría 87 tools: `find_element` slow+wrong; `wait_for_element` OK falso positivo id=4101.
- `smart_find(name=Siete)` sí encontró num7Button vía UIA — routing alternativo funciona.
- NP-12 resuelto con `spy_tree raw` + id=258 — gap distinto (modal offscreen).
- Propuesta `124501` (target window scope) aplicada pero no evita match cross-app con mismo rol Edit.

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| find_element match Cursor search | deteccion | L4 | Sí (este archivo) |
| wait_for_element false OK | deteccion | L4 | Incluido |
| list_elements slow 2381ms | performance | L3 | Backlog notepad-list-elements-slow |
| spy_tree raw NP-12 | routing_tool | L3 | Skill NP-12-goto-line.md met |

No es `ejecucion`: el agente pidió automation_id explícito; el backend devolvió otro id.

## Cambio propuesto

```python
# orchestrator.find_elements — post-process
scoped, meta = filter_elements_to_client_rect(matches, target_hwnd)
if automation_id and not any(m.get("automation_id") == automation_id for m in scoped):
    # fallback spy backend or empty — do not return foreign Edit
    ...
return {"elements": scoped, "scope_meta": meta, ...}
```

Prioridad de match cuando hay target:

1. automation_id exact + inside client rect
2. name/role + inside client rect
3. repo/spy fallback scoped
4. empty + error `no_match_in_target_scope`

## Test de abstracción (L4)

Aplica a cualquier escenario multi-ventana (IDE + app bajo test, MDI, terminal con search box).

## Verificación de duplicados

- **Relacionada, no duplica:** `20260905_210301_list-elements-ancestor-scope-calendar.md` (subárbol popup).
- **Relacionada aplicada:** `124501_list-elements-target-window-scope` — este gap es **falso positivo cross-HWND**.

## Esfuerzo observado

Wave_2: find_element 4698ms; wait_for_element 838ms con id incorrecto; click_element slow en
cadena de find erróneo.

## Criterio de aceptación

- [ ] Unit test: mock matches inside/outside client rect → solo inside retornado.
- [ ] Live Calculadora + Cursor focus: `find_element(automation_id=num7Button)` → num7Button o not found, nunca 4101.
- [ ] `wait_for_element(automation_id=num7Button)` no OK con id ajeno.
- [ ] Timing find_element num7Button <1500ms con spy fast path documentado.
- [ ] Sin regresión Notepad modal scope (171700).

## Beneficios futuros

- Reduce 1 slow + mejora criterio eficiencia objective_met.
- Evita clics/verify en controles del IDE host.
- Alinea find/wait/smart_find con contrato `set_target_window`.

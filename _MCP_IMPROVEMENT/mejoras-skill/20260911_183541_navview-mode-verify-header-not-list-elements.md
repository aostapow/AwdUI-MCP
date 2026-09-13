# discover / execute — verificar modo NavView sin list_elements amplio

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-11 18:35:41 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | awdui-mcp-automejora/references/evaluacion-lab.md |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Versión MCP** | v0.4.0 (check_version: up to date) |

## Resumen

**Problema:** Tras cambiar modo en una app **NavigationView** (lab Calculadora F-06:
`discover_control_interaction` en `TogglePaneButton` + `Standard`, luego
`select_control_item` → Científica), el agente ejecutó `list_elements(max_depth=2)` para
verificar o inventariar → **20892 ms SLOW**, con nodos fuera de contexto (p. ej. enlace
«Móvil» / promo offscope). El cambio de modo ya era verificable sin barrido completo.

**Solución:** Documentar en evaluacion-lab un **atajo VERIFY post-modo**:
(1) `spy_inspect` / `read_element` sobre control `Header` (texto del modo);
(2) opcional `element_exists` en **un** control ancla del modo (`trigButton`, `GraphingControl`,
`DateCalculationOption`, etc. según catálogo del lab, no hardcode en MCP);
(3) **no** usar `list_elements` shallow como único verify tras NavView — reservar B3 para
discover cuando haya affordances nuevas que encolar.

**Dónde:** `evaluacion-lab.md` § Modo B paso B3 (nota NavView) + § execute_flow VERIFY;
referencia en `patterns/control-catalog.md` (NavigationView / ListItem Selection).

## Contexto del turno

- Lab `calculadora-2026-09-11`, flujo **F-06**, `discover_flows` sin flows nuevos (`N=0`).
- ACT OK: `discover_control_interaction` TogglePane + Standard; `select_control_item` Scientific;
  Header «Científica» confirmado.
- Fricción: `list_elements` max_depth=2 → **20892 ms**; `improvements.jsonl` P1;
  `last_cycle.timing_ms=20892`.
- Fix en ciclo (no duplicar): `repo_snapshot_lib` match `Calculadora` / `CalculatorApp.exe` →
  gate **G7** (blockers Teams solo scoped); `repo-snapshot.json` 42 objetos.
- Cobertura lab: ~10/113 tools; `calculator_perfect` elegible; blockers Teams globales intactos.

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| list_elements 20.9 s post-modo | routing_tool | L3 | **Sí** (este archivo) |
| Nodos «Móvil» / offscope en scan | deteccion / performance | L3–L4 | Parcial — ver `20260907_234600` leak scope; no nuevo código aquí |
| discover_control_interaction + select OK | — | — | No — MCP y agente acertaron ACT |
| G7 blockers Teams en state | entorno | L2 | **No** — resuelto en ciclo (`repo_snapshot_lib`) |
| 0 flows encolados discover | — | L2 | No — saturación esperada (`discover_passes_without_new`) |

## Texto propuesto

### VERIFY tras cambio de modo NavView (UWP / WinUI)

Después de `invoke_element` / `select_control_item` en un ítem de navegación:

1. **VERIFY ligero (obligatorio antes de list_elements):**
   - `spy_inspect(automation_id="Header")` o equivalente — nombre contiene el modo esperado.
   - Un solo `element_exists` con `automation_id` ancla del modo (definido en skill de lab /
     `discovered.yaml`, no en servidor MCP).
2. **list_elements** solo si el turno es **discover** y faltan entradas/acciones por encolar
   (B3 con `role` + `max_depth` acotado, tras higiene flyouts — ver `20260907_232300`).
3. Si `discover_passes_without_new >= 1` y el chrome NavView ya está en `flows.json`, **omitir**
   `list_elements` de confirmación; pasar a `execute_flow` pending o subárbol.

## Test de abstracción (L3)

Aplica a cualquier app con NavigationView y header de modo (Calculadora, Configuración, Mail)
sin nombrar automation_ids en la skill genérica — los anclas viven en `discovered.yaml` del lab.

## Verificación de duplicados

| Propuesta existente | Relación |
|---------------------|----------|
| `20260907_232300` flyout dismiss pre-scan | Complementaria — higiene antes de B3 |
| `20260907_232000` NavView verify idempotent | Complementaria — verify en invoke, no post-list |
| `20260907_234600` foreign PID leak | Complementaria — contaminación Teams en list |
| `improvements.jsonl` F-06 friction P1 | Misma evidencia — este archivo formaliza skill |

## Criterios de aceptación (mantenedor)

- [ ] Texto en `evaluacion-lab.md` sin IDs de Calculadora en reglas genéricas del repo MCP.
- [ ] Ejemplo VERIFY en skill de lab Calculadora (`discovered.yaml` / flows) con anclas por modo.
- [ ] Re-ejecutar F-06: Header verify &lt; 3 s total sin `list_elements` obligatorio.
- [ ] `validate_perfect_gate.py` G6 eficiencia no marca SLOW por verify post-modo.

## Beneficios futuros

- Menos turnos discover con `list_elements` &gt; 3 s en UWP NavView cuando el árbol ya está catalogado.
- Alinea OBS→ACT→VERIFY con tools ya usadas con éxito en el mismo turno (`discover_control_interaction`).

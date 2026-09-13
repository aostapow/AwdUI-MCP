# discover_flows raíz — higiene flyouts UWP antes de scan chrome

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-07 23:23:00 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | awdui-mcp-automejora/references/evaluacion-lab.md |
| **Tipo de gap** | performance |
| **Nivel** | L3 |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** En `discover_flows` raíz (`discover_root`), con **flyouts de historial y memoria
abiertos a la vez**, `list_elements(role="Button")` tarda ~2759 ms (SLOW), infla el árbol UIA
y dificulta detectar chrome nuevo (TabItem, menús). El turno terminó con 0 flows nuevos y
`discover_passes_without_new=1` — comportamiento esperado cuando el chrome ya está en
`flows.json`, pero el scan sigue siendo caro e innecesario.

**Solución:** Antes del barrido raíz (paso B3), **cerrar flyouts/popups UWP abiertos**:
`Escape` (1–2×) o re-`invoke_element` del botón padre (`HistoryButton`, `MemoryButton`, toggles
On) hasta confirmar flyout cerrado (`list_elements` sin hijos `ListItem` del panel o
screenshot). Luego `list_elements(role="Button", max_depth=3..4)` acotado al header/NavView.

**Dónde:** `evaluacion-lab.md` § «Fase B — discover_flows» (nuevo subpaso B2.5); referencia
cruzada en `patterns/action-narration.md` («Voy a cerrar flyouts antes de discover…»).

## Contexto del turno

- Lab `calculadora-2026-09-07`, modo `discover_flows` raíz post F-13.
- Observe: chrome TogglePane/History/Memory/NormalAlwaysOnTop ya catalogado (F-02..04, F-24);
  flyouts historial + memoria abiertos; sin TabItem; SystemMenuBar ApplicationFrame 0×0.
- Act: 0 flows encolados; `discover_passes_without_new=1`.
- Fricción: `list_elements` Button **2759 ms** SLOW; doble flyout dificulta scan chrome.
- Evidencia: `runs/calculadora-2026-09-07/evidence.jsonl` L15; MCP v0.4.0.

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| discover_passes_without_new=1 sin flows nuevos | — | L2 | **No** — evaluacion-lab.md § saturación ya lo define |
| list_elements 2759 ms con doble flyout | performance | L3 | **Sí** (este archivo) |
| Scan chrome con popups abiertos | routing_tool | L3 | **Sí** — misma higiene pre-scan |

No es `sintoma_app`: cualquier app UWP/WinUI con múltiples flyouts en header (Calculadora,
Configuración, etc.) se beneficia de cerrar overlays antes de inventario raíz.

## Texto propuesto

### B2.5 — Higiene UI antes de discover raíz

Tras B2 (contexto estable) y **antes** de B3 (`list_elements` / `ascii_ui_view`):

1. `list_windows` + screenshot rápido si hay duda de modales/flyouts.
2. Si hay paneles popup/flyout visibles (historial, memoria, operadores, settings):
   - `Escape` hasta 2 veces, **o**
   - Re-`invoke_element` del botón que abrió el flyout si UIA expone Toggle On.
3. Verificar: flyout cerrado (sin `ListItem` hijos del panel o nombre «No hay historial»).
4. Recién entonces B3 con `role="Button"` y `max_depth` acotado (3–4 en UWP header).

**Nota:** Si `discover_passes_without_new >= 1` y todos los `entry` raíz conocidos ya están
en `flows.json`, preferir pasar a `execute_flow` pending o subárbol antes de repetir scan
completo del header.

## Test de abstracción (L3)

Aplica a Calculadora, apps WinUI con NavView + flyouts, y cualquier ventana con popups
header que no son chrome estable — sin hardcodear `automation_id` en la skill genérica.

## Verificación de duplicados

| Propuesta existente | Relación |
|---------------------|----------|
| `20260907_234600` topmost overlay leak | Distinto — scope PID en pin, no flyout dismiss |
| `2026-09-06-notepad-list-elements-slow` (aplicada) | Fast path MenuItem Win32 — complementario |
| Advisor 2026-09-07 23:40 discover F-24 | Mismo síntoma list slow + flyout memoria — **ampliado** aquí con doble flyout + contador saturación |
| `211201_calculator-perfect-gate-checklist` | Gate perfect — no cubre discover hygiene |

## Esfuerzo observado

Turno discover raíz ~2759 ms en una sola tool; 0 flows agregados; contador saturación
incrementado innecesariamente con árbol inflado.

## Criterio de aceptación

- [ ] Texto en evaluacion-lab.md sin IDs fijos de Calculadora en reglas genéricas (ejemplos OK)
- [ ] Menciona alternativa ESC vs re-invoke toggle
- [ ] Enlaza con `discover_passes_without_new` para evitar scans repetidos caros
- [ ] Próximo discover_root Calculadora con flyouts cerrados: `list_elements` Button <1500 ms o evidencia timing en evidence.jsonl

## Beneficios futuros

- Menor latencia en alternancia execute_flow ↔ discover_flows.
- Chrome scan más fiable para TabItem/menús cuando flyouts no ocultan header.
- Reduce falsos «sin novedad» costosos cuando el árbol está inflado por UI transitoria.

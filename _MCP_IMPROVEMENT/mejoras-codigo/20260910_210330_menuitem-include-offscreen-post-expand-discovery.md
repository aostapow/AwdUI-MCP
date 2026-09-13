# list_elements / get_snapshot — MenuItem offscreen tras expand ribbon SplitButton

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 21:03:30 |
| **Usuario sesión** | ariel.ostapow |
| **Tool afectada** | `list_elements`, `get_snapshot`, `expand_element` |
| **Módulo** | `detection/orchestrator.py`, `detection/backends/uia_backend.py`, `tools/ui_automation.py` |
| **Tipo de gap** | deteccion |
| **Nivel** | L4 |
| **Versión MCP** | 0.4.0 (up to date) |

## Resumen

**Problema:** Tras `expand_element` en SplitButton de cinta (Explorador «Nuevo elemento»), los
`MenuItem` hijos (p. ej. «Carpeta») existen en UIA pero quedan con `visible=false` / fuera del
filtro de scope; con `include_offscreen=false` (default) **no aparecen** en `get_snapshot` ni
`list_elements(role=MenuItem)`, obligando al agente a descubrir el parámetro manualmente.

**Solución:** (1) En `orchestrator`, si `role` es `MenuItem` (o escaneo acotado post-expand),
default `include_offscreen=true` (paridad con `TreeItem`/`ListItem`/`TabItem`). (2) Opcional:
respuesta de `expand_element` con `suggested_next_params: { include_offscreen: true, role: MenuItem }`
cuando el expand abre menú popup. (3) Dedupe de instancias duplicadas del mismo flyout (bbox
disjuntos, mismo `name`) priorizando nodo con bbox intersectando client rect o menor área fantasma.

**Dónde:** `orchestrator.py` § default offscreen; `uia_backend.py` dedupe; `MCP_TOOLS_REFERENCE.md`.

## Contexto del turno

- Lab `escritorio-windows-2026-09-10`, `discover_flows` subárbol **F-98** («Nuevo elemento»).
- OBS/ACT: `invoke` Inicio 605 ms; `expand_element` 813 ms; encolado **F-163..F-175** (13 flows).
- VERIFY: `get_snapshot(include_offscreen=true)` reveló «Carpeta» + 12 tipos; sin flag, inventario incompleto.
- `improvements.jsonl`: flyout duplicado UIA (bbox 1215 vs 1678); `fix_in_cycle: not_attempted`.
- Turno discover OK (<3 s act principal); `objective_met` sigue false (criterios globales / Teams).

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| Carpeta ausente sin include_offscreen | deteccion | L4 | Sí (este archivo) |
| Flyout MenuItem duplicado en árbol | deteccion | L4 | Sí (dedupe en mismo cambio) |
| Escape no cierra flyout (minimal focus) | entorno | L2 | No — friction F-98; click dismiss |
| Discover encolado correcto con workaround | ejecucion | — | No propuesta skill redundante sola |

## Cambio propuesto (pseudodiff)

```python
# orchestrator.py — junto a TreeItem/ListItem/TabItem
_MENU_OFFSCREEN_ROLES = ("treeitem", "listitem", "tabitem", "menuitem")

if role_lower in _MENU_OFFSCREEN_ROLES and not include_offscreen:
    include_offscreen = True  # document in JSON: include_offscreen_effective
```

```python
# uia_backend.py o list merge — al flatten snapshot
def _dedupe_menu_flyout_instances(nodes: list[DetectedElement]) -> list:
    # group by (role, normalized_name); keep one with max intersection(client_rect) or visible=True
```

```python
# expand_element success payload (opcional)
if expanded_role in ("SplitButton", "MenuItem") and menu_opened:
    result["discovery_hint"] = {
        "list_elements": {"role": "MenuItem", "max_depth": 4, "include_offscreen": True},
    }
```

## Test de abstracción (L4)

Win32 ribbon/menús (Explorador, Notepad menú, Office-style SplitButton): cualquier flyout cuyos
items UIA marcan offscreen mientras el popup está abierto.

## Verificación de duplicados

| Propuesta | Acción |
|-----------|--------|
| `20260906_214000_list-elements-treeitem-sidebar-discovery` | Paralelo — sidebar TreeItem; no merge |
| `20260906_214500_list-elements-treeitem-electron-perf-uia-first` | Paralelo — Electron |
| `20260910_195126_discover-subtree-flyout-menuitem-scan` | **Complemento skill** — routing discover; este doc es default MCP |

## Esfuerzo observado

Agente debió conocer `include_offscreen=true` para encolar F-163; riesgo de perder 13 flows en
discover sin snapshot explícito (turno actual lo aplicó correctamente tras gap conocido).

## Criterios de aceptación

- [ ] `tests/test_list_elements.py`: fixture o mock con MenuItem `visible=false` incluido cuando `role=MenuItem`.
- [ ] Live Explorador F-98 discover: `get_snapshot(max_depth=5)` **sin** pasar flag devuelve «Carpeta».
- [ ] Respuesta incluye `include_offscreen_effective` cuando se auto-eleva.
- [ ] Documentar en `MCP_TOOLS_REFERENCE.md` § defaults por rol.
- [ ] Si dedupe activo: snapshot no lista dos «Carpeta» con bbox incoherentes.

## Beneficios futuros

Discover subárbol ribbon sin parámetro oculto; menos falsos «0 MenuItem»; alinea lab F-163..175 con
contrato MCP agnóstico (no hardcode Explorer).

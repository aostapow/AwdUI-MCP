# discover_flows: inventario TabItem en modal owned antes de find por nombre

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 20:15:11 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | `awdui-mcp-automejora/references/evaluacion-lab.md` + `patterns/active-window.md` |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Versión MCP** | v0.4.0 (up to date) |

## Resumen

**Problema:** En `discover_flows` subárbol **F-22** (modal ACL `#32770`), el agente ejecutó
`find_element` por pestañas opcionales («Deshabilitar herencia», «Auditoría») sin inventario previo.
Cada miss disparó depth ladder → **~23 s** por probe (`find_neg` 23674 ms en `evidence.jsonl`);
`list_elements` previo **11.5 s** por scope padre+modal mezclado.

**Solución:** Tras `list_windows` confirme modal mismo PID: (1) `focus_window` título modal o
`window_handle` del `#32770`; (2) **una** pasada `list_elements(role="TabItem"|"Button", max_depth=6)`
solo en ese contexto; (3) encolar flujos solo para nodos devueltos; (4) **no** `find_element` por
chrome localizado (p. ej. pestaña Auditoría en ES puede no existir). Opcional: `get_snapshot(max_depth=4)`
para señales sin ladder.

**Dónde:** `evaluacion-lab.md` § discover subárbol modal; cross-ref `active-window.md` (título modal).

## Contexto del turno

- Lab `escritorio-windows-2026-09-10`, discover `subtree:F-22`, enqueue F-75..F-84, verify OK WARN.
- Señales útiles ya encontradas: `ButtonViewAce`, `LUAChangeButton`, Tab «Acceso efectivo».
- F-83 cancelado en flows: «TabItem Auditoría no encontrado en UIA (find 23s)».
- `improvements.jsonl`: find «Permisos» fuzzy matchea `ResetAclTreePermission` — evitar find por
  substring sin `automation_id`.

## Análisis del gap

| Fricción | tipo_gap | Propuesta |
|----------|----------|-----------|
| find 23s Tab Auditoría NOT FOUND | performance | Código `20260910_195126_find-element-name-search-negative-wall-clock` |
| list 11.5s explorer+modal | deteccion | Código `20260910_201130_owned-modal-auto-scope` (+ `list_elements`) |
| Probes opcionales sin inventario | routing_tool | **Este archivo** |

No es `ejecucion` pura: la metodología no detalla discover en modales owned; el agente repitió patrón flyout/ribbon incorrecto.

## Texto propuesto

### discover_flows — modal `#32770` mismo proceso

1. Tras abrir el diálogo: `list_windows` → anotar HWND/título modal.
2. `focus_window` modal (hasta que `scope_mode=auto` resuelva `owned_modal` en servidor).
3. `list_elements(role="TabItem", max_depth=6)` — registrar nombres exactos; **omitir** tabs no listados.
4. Botones ACL: preferir `automation_id` conocidos (`ButtonViewAce`, `LUAChangeButton`) antes de `name` fuzzy.
5. Miss esperado: abortar en <3 s cuando exista `negative_fast` (propuesta código); no reintentar ladder en discover.

## Test de abstracción (L3)

Cualquier lab con diálogo sistema Win32/WinForms mismo PID (Notepad Buscar, permisos carpeta, Propiedades).

## Verificación de duplicados

| Propuesta | Relación |
|-----------|----------|
| `discover-subtree-flyout-menuitem-scan` | Complemento — flyouts, no modales |
| `find-element-name-search-negative-wall-clock` | Performance; no sustituye inventario |
| `owned-modal-auto-scope` | Scope servidor; skill sigue pidiendo focus hasta fix |

## Esfuerzo observado

>45 s en discover-F-22 solo en `list_elements` + dos `find_neg` (~23 s c/u); 14 flows `met`, cola ~84.

## Criterios de aceptación

- [ ] Texto sin «Explorador» como único ejemplo; patrón modal genérico.
- [ ] En replay discover-F-22: sin `find_element` >5 s por tabs no inventariadas.
- [ ] Referencia en `evaluacion-lab.md` discover subárbol.

## Beneficios futuros

- Reduce latencia acumulada lab Escritorio sin esperar solo fix `negative_fast`.
- Evita falsos positivos fuzzy (`Permisos` → `ResetAclTreePermission`).

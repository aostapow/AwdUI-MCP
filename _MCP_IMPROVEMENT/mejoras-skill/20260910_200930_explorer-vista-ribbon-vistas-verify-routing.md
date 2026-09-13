# Explorer cinta Vista — botón Vistas (layout): act + verify sin find negativo

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 20:09:30 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | `awdui-mcp-automejora/references/evaluacion-lab.md`, `patterns/control-catalog.md` § Button / MultipleView |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Versión MCP** | v0.4.0 (check_version 2026-09-10, up to date) |

## Resumen

**Problema:** Lab Escritorio **F-18** (menú **Vistas** en cinta Vista): `invoke_element` en
`Button: Vistas` falló (**459 ms**); `click_element` abrió el menú OK (**1709 ms**). Tras
`list_elements(role=MenuItem)` (**1461 ms**), el agente buscó **«Iconos extragrandes»** con
`find_element` → **NOT FOUND 27586 ms** aunque el criterio del flujo solo exige menú/galería
visible (verify posterior **ListItem Detalles 249 ms** + screenshot).

**Solución:** Documentar secuencia ribbon Win32 Vista: (1) `invoke_element` → si fail,
`click_element(name=…, role=Button)` (paridad patterns con propuesta código
`195530_invoke-element-role-menuitem-act-parity`, ampliar mentalmente a **Button** ribbon);
(2) **VERIFY** con `list_elements(role=MenuItem|ListItem)` acotado o screenshot de galería
«Diseño» — **no** `find_element` por modos de vista opcionales no listados en
`discovery_signals` / `success_criteria`; (3) cerrar con Escape sin cambiar layout.

**Dónde:** Bloque «Explorer — cinta contextual Vista» en `evaluacion-lab.md` o
`patterns/win32-explorer-ribbon.md` (nuevo patrón cross-app).

## Contexto del turno

- Lab `escritorio-windows-2026-09-10`, **13/64 met** tras F-18.
- Evidence: `evidence.jsonl` F-18 WARN invoke+find_neg SLOW; `flows.json` notas actualizadas.
- `improvements.jsonl`: fricción invoke + find 27s; `fix_in_cycle: not_attempted`.

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| find «Iconos extragrandes» 27s | performance + routing_tool | L3/L4 | Código: `195126_find-element-name-search-negative-wall-clock` (no duplicar) |
| invoke Vistas fail, click OK | tool_gap | L4 | Código: `195530_invoke-element-role-menuitem-act-parity` (+ Button ribbon en criterio) |
| Probe layout opcional vs criterio | routing_tool | L3 | **Este archivo** |

No es `ejecucion` pura en invoke: el MCP aún no unifica cascada invoke/click (backlog P1).
El find 27s es gap MCP aunque el agente no debiera buscar chrome opcional.

## Texto propuesto

### Explorer — cinta Vista, botón Vistas

1. **Pre:** Tab/cinta **Vista** activa (`invoke_element` TabItem Vista si aplica).
2. **ACT:** `invoke_element(name="Vistas", role="Button")` → si `success=false`,
   `click_element(name="Vistas", role="Button")`.
3. **VERIFY (elegir uno):**
   - `list_elements(role="MenuItem", max_depth=6)` con ≥1 ítem de diseño visible, o
   - `find_element(name="Detalles", role="ListItem")` solo si ya apareció en listado previo, o
   - screenshot con galería «Diseño» / menú desplegado.
4. **Prohibido en VERIFY de «menú visible»:** `find_element` por modos no requeridos
   (ej. «Iconos extragrandes») — miss debe resolverse con listado, no búsqueda negativa larga.
5. **Cierre:** `press_key` Escape; probe ventana limpia.

Tras WARN invoke fail: `repo_hints_set(append=true)` — `nota: Vista ribbon Vistas — click_element role=Button tras invoke fail`.

## Test de abstracción (L3)

Cualquier ventana Win32 con dropdown de vista en ribbon (Explorador, diálogos con
**MultipleView** / galería de layout): mismo orden act→list/verify, sin find especulativo.

## Verificación de duplicados

| Propuesta | Relación |
|-----------|----------|
| `20260910_195126_find-element-name-search-negative-wall-clock` | Complemento código — F-18 añade evidencia 27s |
| `20260910_195530_invoke-element-role-menuitem-act-parity` | Ampliar criterio live replay: F-18 Button Vistas |
| `20260910_195330_discover-subtree-search-ribbon-splitbutton-routing` | Hermana — cinta búsqueda, no Vista layout |

## Esfuerzo observado

F-18 met con WARN; ~28 s desperdiciados en un solo find negativo; lab efficiency G6.

## Criterio de aceptación

- [ ] Texto sin paths lab específicos salvo ejemplo «Vistas» genérico Explorer.
- [ ] Enlaza explícitamente a backlog invoke parity y find fast-fail (sin reimplementar).
- [ ] Replay F-18: sin find «Iconos extragrandes»; verify < 3 s adicional tras list MenuItem.

## Beneficios futuros

Flujos F-19+ (columnas, detalles) parten de menú Vistas abierto sin latencia discover;
menos falsos P1 en `improvements.jsonl` por probes opcionales.

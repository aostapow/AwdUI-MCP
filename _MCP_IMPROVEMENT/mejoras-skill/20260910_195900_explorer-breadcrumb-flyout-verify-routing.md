# Explorer barra direcciones — VERIFY breadcrumbs (SplitButton, no MenuItem)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 19:59:00 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | `awdui-mcp-automejora/references/evaluacion-lab.md`, `patterns/control-catalog.md` § SplitButton |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **MCP versión** | v0.4.0 |

## Resumen

**Problema:** Tras `invoke_element` en **SplitButton** «Todas las ubicaciones» (flyout de
migas/breadcrumbs), el agente ejecutó `list_elements(role="MenuItem")` esperando segmentos de
ruta. UIA devolvió solo ruido de **menú Sistema** de la barra de título; no hay segmentos
encolables vía MenuItem. El flujo **met** solo con **screenshot** + texto visible en barra de
direcciones — workaround repetible pero no documentado.

**Solución:** Bloque en **evaluacion-lab** § execute VERIFY (Win32 shell / Explorador):

1. **ACT:** `invoke_element` / `expand_element` en SplitButton de breadcrumbs (patrón Invoke/ExpandCollapse).
2. **VERIFY (orden):**
   - `list_elements(role="ListItem", max_depth=5)` y/o `role="Hyperlink"` en el popup de ruta;
   - si 0 ítems útiles → `spy_tree(max_depth=4)` acotado al contenedor de barra de direcciones
     (no barrido raíz);
   - leer **Value** del Edit/combo de direcciones si expone ruta completa;
   - **screenshot(scope=window)** como verify final aceptable cuando UIA no materializa segmentos
     (documentar como último paso, no sustituto de list sin intentar ListItem/Hyperlink).
3. **Prohibido:** asumir que todo flyout Win32 es `MenuItem` (contraste con
   `discover-subtree-flyout-menuitem-scan` — menús contextuales sí; breadcrumbs no).

**Dónde:** `evaluacion-lab.md` tabla «Subárbol / flyout» — tercera fila **Barra direcciones /
breadcrumbs**; nota en `control-catalog.md` SplitButton + Address band.

## Contexto del turno

- F-12 **met** (lab 11/56): invoke 1973 ms OK; `list_elements` MenuItem 895 ms sin segmentos;
  screenshot `awdui_1789081056367_12.png`; Escape; probe 356 ms.
- `improvements.jsonl`: workaround VERIFY visual + ruta en barra.

## Análisis del gap

| Fricción | tipo_gap | L | Propuesta |
|----------|----------|---|-----------|
| MenuItem tras SplitButton breadcrumbs | routing_tool | L3 | Este archivo |
| Segmentos no en árbol UIA | deteccion | L3 | Skill verify + posible hint MCP (propuesta código hermana) |
| invoke OK | — | — | No código |

## Texto propuesto

### Barra de direcciones — flyout «Todas las ubicaciones» (execute VERIFY)

Después de abrir el flyout (SplitButton):

| Paso | Tool | Criterio |
|------|------|----------|
| 1 | `list_elements(role="ListItem", max_depth=5)` | ≥1 segmento de ruta con nombre de carpeta |
| 2 | `list_elements(role="Hyperlink", max_depth=5)` | Alternativa si ListItem vacío |
| 3 | `read_element` / Value en control de dirección | Ruta completa como texto |
| 4 | `screenshot(scope=window)` | Ruta legible en barra; cerrar flyout Escape |

**No** usar solo `list_elements(role="MenuItem")` — en Explorador Win11 ES suele mezclar ítems
del menú **Sistema**, no la jerarquía de carpetas.

## Test de abstracción (L3)

Cualquier shell Win32 con breadcrumbs desplegables (Explorador, diálogos Abrir/Guardar con
barra de ruta) — no AST ni producto interno.

## Verificación de duplicados

| Propuesta | Acción |
|-----------|--------|
| `20260910_195126_discover-subtree-flyout-menuitem-scan` | **Complementaria** — añadir fila breadcrumbs vs menú contextual al implementar |
| `20260910_195330_discover-subtree-search-ribbon-splitbutton-routing` | Hermana — cinta SplitButton, no flyout de ruta |

## Esfuerzo observado

~895 ms list inútil + dependencia screenshot; flujo met sin encolar hijos (subtree_discovered=false).

## Criterios de aceptación (mantenedor)

- [ ] Texto sin rutas lab ni nombres de carpeta concretos.
- [ ] Distinción explícita tres flyouts: MenuItem contextual, SplitButton cinta, breadcrumbs dirección.
- [ ] Re-ejecutar F-12: ListItem/Hyperlink antes de screenshot.

## Beneficios futuros

Menos falsos VERIFY; alinea execute con discover; reduce screenshot-only en matriz de calidad MCP.

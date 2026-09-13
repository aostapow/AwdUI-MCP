# Cinta Explorer — homónimo TabItem vs Button (ej. Compartir)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 20:22:15 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | `awdui-mcp-automejora/references/patterns/win32-explorer-ribbon.md` (nuevo) o `evaluacion-lab.md` § Explorer |
| **Tipo de gap** | routing_tool |
| **Nivel** | L4 |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** En la pestaña contextual **Compartir** del Explorador, UIA expone **dos** controles
con nombre «Compartir»: un **TabItem** (pestaña de cinta) y un **Button** (grupo Enviar).
`find_element` / `click_element` sin `role` puede resolver el TabItem; el flujo F-23 requiere el
**Button** del panel Enviar. El turno quedó `partial` con workaround `ListItem` probe +
`element_at_point` y filtro espacial (`bbox.y > 100`).

**Solución:** Patrón obligatorio antes de actuar en cinta contextual:

1. Tras activar la pestaña (TabItem), **siempre** pasar `role="Button"` (o `control_type=Button` en
   `click_element_hwnd`) para affordances de comando en la banda inferior de la cinta.
2. Si el nombre colisiona: `list_elements(role="Button", max_depth=4)` en el subárbol de la
   pestaña activa y elegir por **bbox** (botón de comando suele estar **debajo** de la fila de tabs;
   documentar umbral relativo al `client rect` de la ventana, no coords absolutas en skill).
3. **No** usar `expand_element` en el homónimo — en F-23 abrió menú de sistema.
4. VERIFY flyout: screenshot o `wait_for_change`; flyout «Enviar» puede ser opaco a UIA — Escape
   cierra sin envío (criterio F-23).

**Dónde:** Patrón cross-app en `patterns/`; nota en lab `flows.json` F-23 ya documenta síntoma.

## Contexto del turno

- **F-23** `partial`: `discovery_signals`: `Button: Compartir (panel Enviar)`.
- Evidence: probe ListItem; click (613,172); flyout no visible UIA; `click_element_hwnd` falló (ver
  propuesta código `20260910_202207_click-element-hwnd-missing-do-click-import`).

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| Clic en TabItem en lugar de Button | routing_tool | L4 | **Sí (este archivo)** |
| `click_element_hwnd` roto | tool_gap | L4 | Propuesta código hermana |
| find neg Copiar/Bluetooth >20s | performance | L3 | `195126_find-element-name-search-negative-wall-clock` — no duplicar |

## Texto propuesto

### Homónimos nombre en cinta Win32 (TabItem + Button)

Cuando `list_elements` o discover muestran **mismo `name`** en **TabItem** y **Button**:

| Objetivo | Rol UIA | Evitar |
|----------|---------|--------|
| Cambiar pestaña de cinta | TabItem / `invoke_element` | `click_element` sin role |
| Comando en grupo (Enviar, Seguridad, …) | **Button** | TabItem homónimo |
| Verificar pestaña activa | TabItem `SelectionItem.IsSelected` | OCR del título |

Secuencia tipo «abrir flyout Compartir»:

1. Confirmar pestaña Compartir activa (TabItem o ya en contexto F-06).
2. `click_element(name="Compartir", role="Button")` o `invoke_element` con role Button.
3. Si miss: `list_elements(role="Button", max_depth=4)` → filtrar por nombre + banda Y en cinta.
4. Cerrar con Escape; no completar envío real.

## Test de abstracción (L4)

Office ribbon, Explorador Vista/Compartir/Copiar, cualquier UIA con TabItem + Button mismo texto.

## Verificación de duplicados

| Propuesta | Acción |
|-----------|--------|
| `20260910_195330_discover-subtree-search-ribbon-splitbutton-routing` | Complementaria — discover SplitButton; este ítem — **act** con homónimo Tab/Button |
| `20260910_200930_explorer-vista-ribbon-vistas-verify-routing` | Hermana Vista; merge opcional en un solo `win32-explorer-ribbon.md` |

## Esfuerzo observado

F-23 partial; coords manuales; HWND tool inutilizable por NameError.

## Criterios de aceptación (mantenedor)

- [ ] Texto sin coords absolutas del lab.
- [ ] Tabla TabItem vs Button reproducible en otra pestaña de cinta.
- [ ] Tras skill + fix HWND: re-VERIFY F-23 en lab escritorio.

## Beneficios futuros

Menos `element_at_point` en cintas; flujos Compartir/Vista encolables sin `partial` por homónimo.

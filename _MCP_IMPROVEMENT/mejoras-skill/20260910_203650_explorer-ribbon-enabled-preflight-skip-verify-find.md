# Ribbon Explorer: preflight is_enabled y omitir verify find si act bloqueado

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 20:36:50 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | `awdui-mcp-automejora/references/evaluacion-lab.md` + `patterns/object-repository.md` |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Versión MCP** | v0.4.0 (up to date) |

## Resumen

**Problema:** En flujos lab tipo «Abrir panel Historial», el agente invoca/clickea el botón ribbon y luego
verifica el panel con `find_element` aunque `spy_inspect` ya mostró `is_enabled=false` (archivo probe sin
historial de versiones). Eso dispara **find neg ~26 s** (misma familia que F-08) y marca PARTIAL sin
clasificar el bloqueo como **fixture/precondición**.

**Solución:** (1) Tras localizar el `Button` ribbon, **leer estado** (`spy_inspect` o `read_element` /
`get_element_properties`) y comprobar `is_enabled`/`enabled` **antes** de invoke/click/atajos. (2) Si
`is_enabled=false`: VERIFY = `fixture_blocked` (PARTIAL documentado), **no** buscar chrome del panel
(`Historial de versiones`, etc.). (3) Persistir lección: `repo_hints_set` con `precondicion:` (tras
`repo_capture` del botón) o nota en `flows.json` del flujo seed.

**Dónde:** evaluacion-lab § execute_flow VERIFY; bloque nuevo en `patterns/winforms.md` o
`patterns/uwp-navview-patterns.md` § controles ribbon dependientes de contexto de archivo.

## Contexto del turno

- Lab `escritorio-windows-2026-09-10`, **F-29** `partial`.
- Probe `.txt` local → `spy_inspect` **Historial** `is_enabled=False`; invoke/Alt+H+H sin panel.
- VERIFY: `find_element` NOT FOUND **26542 ms**; limpieza Delete de «Nueva carpeta» accidental.
- **Sin** `repo_hints_set` (regla lab/object-repository no aplicada en cierre).

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| find neg 26s tras act inútil | performance | L4 | No — consolidar `20260910_195126_find-element-name-search-negative-wall-clock` |
| Act sin leer is_enabled | routing_tool | L3 | Sí (este archivo) |
| Archivo sin versiones | sintoma_app / fixture lab | L1 | Nota en flows + precondicion hint, no código MCP |
| No repo_hints_set | ejecucion | — | No — ya `object-repository.md` + `20260910_200820_repo-hints-set` |

## Texto propuesto

### Controles ribbon dependientes del archivo (preflight)

Antes de **act** sobre un `Button` cuya affordance depende del ítem seleccionado (Historial, versiones,
comparar, etc.):

1. `spy_inspect(name=…)` o `read_element` → registrar `is_enabled` / `enabled`.
2. Si **false**: no invoke ni atajos repetidos; VERIFY = `fixture_blocked` con mensaje explícito
   (ej. «requiere historial de versiones / OneDrive / copias previas»).
3. **Prohibido** en ese caso: `find_element` del panel hijo para «demostrar» fallo — esperar miss rápido
   o omitir verify (evita 20–30 s hasta fix `negative_fast`).
4. Cierre: si el control ya está en repo → `repo_hints_set` con `precondicion: …`; si no →
   `repo_capture` mínimo + hint.

### Lab Escritorio — F-29 (nota operativa, L1)

Seed/probe: usar archivo con **historial de versiones** habilitado o marcar flujo `blocked_fixture` en
`flows.json` cuando el probe sea `.txt` plano sin versiones.

## Test de abstracción (L3)

Aplica a cualquier ribbon/toolbar donde UIA expone `IsEnabled=false` hasta cumplir precondición (guardar
deshabilitado, «Siguiente» en wizard, etc.) — no solo Explorador.

## Verificación de duplicados

| Propuesta | Relación |
|-----------|----------|
| `20260910_195126_find-element-name-search-negative-wall-clock` | Complemento código — miss rápido |
| `20260910_200820_repo-hints-set-missing-path-actionable-error` | Persistir `precondicion` tras capture |
| `20260905_120902_stale-element-cache-invalidate` | Distinto — stale vs disabled por contexto |
| AST `btnGuardar` + `is_enabled` | Mismo patrón verify-before-act; generalizar a lab/ribbon |

## Esfuerzo observado

F-29: tab 1294 ms; find neg 26542 ms; invoke ListItem 4221 ms; veredicto PARTIAL WARN SLOW.

## Criterio de aceptación

- [ ] Texto en skill genérica sin hardcodear solo «Historial» como único ejemplo (≥2 roles/contextos).
- [ ] evaluacion-lab menciona `fixture_blocked` vs `fail` en VERIFY.
- [ ] Cross: patrón citado desde winforms o navview patterns.

## Beneficios futuros

Turnos lab dejan de quemar ladder en verify imposible; `mcp-quality` mejora al separar gap MCP de fixture
de entorno.

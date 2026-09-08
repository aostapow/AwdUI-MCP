# Evaluación con app de laboratorio (genérico)

El usuario solo indica **el nombre de la aplicación** (ej. «Calculadora», «Bloc de notas», «Microsoft Teams»).  
Opcionalmente puede listar **unos pocos flujos funcionales** conocidos al inicio (ej. «suma 2+2», «guardar archivo»).  
El agente **autodetecta** framework, ventana y launch; el **catálogo de flujos crece** durante la corrida.

## Cuándo aplica

1. Pedido explícito: «evaluá el MCP con {nombre}», «usá {nombre} como lab», o  
2. `state.json` → `active_lab: "{nombre}"` (texto libre, mismo nombre que dijo el usuario).

Sin eso → **solo automejora MCP**. No inventar lab.

## Entrada mínima

| Campo | Quién lo define | Ejemplo |
|-------|-----------------|---------|
| Nombre de app | **Usuario** | `Calculadora` |
| Flujos seed (opcional) | **Usuario** — pueden ser muy pocos | `2+2`, `cambiar a modo científico` |
| `active_lab` | Usuario o agente al iniciar corrida | `Calculadora` |
| `active_run` | Agente | `calculadora-2026-09-08` (slug + fecha) |

**No pedir** al usuario: `framework`, `launch`, `target_window`, `automation_id`, locale.

### Inicio de corrida

1. Crear `runs/{active_run}/`.
2. Crear `flows.json` desde [flows.template.json](../../../lab-apps/flows.template.json):
   - Si el usuario listó flujos en el turno → uno por fila `source: seed`, `status: pending`.
   - Si existe `lab-apps/seeds/{slug}.json` → copiar/adaptar.
   - Si no hay seeds → `flows: []` (válido; el primer turno post-autodetect será `discover_flows`).

---

## Fase 0 — Autodetección (obligatoria antes de interactuar)

```
PASO 1 — list_windows / list_desktop_windows
PASO 2 — launch_app si falta
PASO 3 — focus_window + set_target_window
PASO 4 — detect_framework
PASO 5 — detection_health
PASO 6 — observe_ui_tool o ui_fingerprint (baseline)
```

Salida: `runs/{active_run}/discovered.yaml`.

Si autodetección falla → **blocker** en `state.json`.

---

## Catálogo de flujos — `runs/{active_run}/flows.json`

Archivo **vivo** de la corrida. Es un **árbol funcional**: ramas (ventanas/menús/modos) e hijos (acciones dentro de ese contexto).

### Tipos de flujo (`kind`)

| `kind` | Qué es | Cuándo crearlo |
|--------|--------|----------------|
| `entry` | **Entrar** a un contexto nuevo (menú, modal, tab, modo, panel) | Al ver una affordance que abre otra UI — **solo este flujo**, sin hijos aún |
| `action` | **Hacer** algo dentro de un contexto ya abierto | Tras `entry` padre en `met` y turno `discover_flows` en ese subárbol |

### Campos clave

| Campo | Uso |
|-------|-----|
| `id` | `F-01`, `F-02`, … secuencial |
| `kind` | `entry` \| `action` |
| `parent_id` | `null` = raíz; si es hijo → id del `entry` que abre el contexto |
| `subtree_discovered` | Solo en `entry`: `false` hasta escanear hijos; `true` cuando ya se listaron acciones del submenú/ventana |
| `window_context` | Dónde aplica **antes** de ejecutar |
| `window_after` | Estado/UI esperada tras un `entry` (menú abierto, modal visible) |
| `title` / `description` | Lenguaje funcional, sin automation_ids |
| `source` | `seed` \| `user` \| `discovered` |
| `status` | `pending` → `exploring` → `met` \| `partial` \| `blocked` \| `cancelled` |
| `priority` | Menor = antes (entre hermanos del mismo `parent_id`) |
| `success_criteria` | Verificación observable |
| `discovered_from` | Flujo o contexto que motivó el descubrimiento |
| `discovery_signals` | Affordances UIA (roles, names) |

`cycle.discover_scope` (opcional): `{ "parent_flow_id": "F-02", "window_context": "menú Formato" }` mientras se descubre un subárbol.

---

## Descubrimiento en dos fases (ramas inteligentes)

Objetivo: **mapear funcionalidades completas**, no una lista plana de clicks.

### Fase 1 — Ver affordance en ventana A (raíz)

Ejemplo: en Bloc de notas principal aparece `MenuItem "Formato"` que no estaba en seeds.

**Solo** agregar:

```json
{
  "id": "F-05",
  "kind": "entry",
  "title": "Ingresar al menú Formato",
  "parent_id": null,
  "subtree_discovered": false,
  "window_context": "Bloc de notas - principal",
  "window_after": "menú Formato desplegado",
  "discovery_signals": ["MenuBar > Formato"]
}
```

**Prohibido en Fase 1:** inventar hijos («cambiar fuente», «ajuste de línea») sin haber abierto el menú.

### Fase 2 — Tras `entry` en `met` (ventana B o menú expandido)

Cuando `F-05.status === met` y `subtree_discovered === false`:

1. Turno `discover_flows` con `discover_scope.parent_flow_id = F-05`.
2. Reabrir entrada si hace falta (un paso de `execute_flow` en F-05) para dejar el menú visible.
3. Escanear **solo** lo accesible en ese contexto (`list_elements`, menú desplegado, modal hijo).
4. Por **cada** ítem coherente visible en el mismo barrido → flujo `kind: action` con `parent_id: F-05` (todos en un turno discover, no de uno en uno):

```json
{
  "id": "F-06",
  "kind": "action",
  "title": "Activar ajuste de línea",
  "parent_id": "F-05",
  "window_context": "menú Formato abierto",
  "discovery_signals": ["MenuItem: Ajuste de línea"]
}
```

5. Marcar `F-05.subtree_discovered = true` (aunque haya 0 hijos — saturación local).
6. Limpiar o actualizar `cycle.discover_scope`.

### Ramificación ventana 1 → ventana 2

| Situación | `entry` | Hijos `action` |
|-----------|---------|----------------|
| Menú desplegable (misma ventana) | Abrir menú | Items del menú |
| Modal nuevo (`#32770`, «Guardar como») | Abrir diálogo | Nombre, tipo, botones Guardar/Cancelar |
| NavView / tab | Cambiar sección | Acciones del panel activo |
| Subventana hija | Enfocar / `set_target_window` hijo | Controles dentro del hijo |

Cada **modal o ventana hija** puede ser un `entry` hijo de otro `entry` si abre un contexto distinto (`parent_id` encadenado).

### Orden de ejecución (árbol)

1. No ejecutar `action` si `parent_id` no está `met`.
2. Priorizar `entry` pendientes en raíz antes que acciones sueltas en raíz.
3. Tras `entry` `met` sin subárbol → priorizar `discover_flows` en ese scope antes de profundizar otra rama.
4. Entre hermanos (`mismo parent_id`): menor `priority` primero.

---

## Ciclo lab por turno (alternar ejecutar ↔ descubrir)

Después de `autodetect`, **cada turno** hace exactamente **una** de estas dos cosas:

| Modo | Qué cuenta como «un turno» |
|------|----------------------------|
| `execute_flow` | **Un paso** de **un** flujo (OBS→ACT→VERIFY) |
| `discover_flows` | **Un escaneo** de la pantalla — puede **encolar muchos** flujos nuevos en `flows.json` |

La cola crece en discover; la ejecución consume la cola de a un paso por turno.

### Modo A — `execute_flow`

Ejecutar **un paso** del flujo pendiente con mayor prioridad (`pending` o `exploring`):

1. Marcar flujo `status: exploring`.
2. Seguir [metodologia-ui.md](metodologia-ui.md) fases 0–6 **acotadas** a ese flujo.
3. OBS → ACT → VERIFY → línea en `evidence.jsonl` con `flow_id`.
4. **Chat:** bloque «Voy a» antes de cada tool (ver [action-narration.md](patterns/action-narration.md)).
5. **Repo:** si el control es estable → anotar `repo_path` en el flujo / `element-map.md`; `repo_capture` si no existe; tras fricción → `repo_hints_set` (ver [object-repository.md](patterns/object-repository.md)). Antes de `repo_action` → `repo_hints`.
6. Si `success_criteria` cumplido → `status: met`; si no, dejar `exploring` o `partial`.
7. `cycle.last_mode = execute_flow`.

Un turno = un paso agentico verificable, no un script batch del flujo entero.

### Modo B — `discover_flows`

**Un turno de discover = un barrido de la UI actual, N flujos encolados.**  
Si la pantalla expone 10 acciones nuevas (ítems de menú, botones, tabs), agregar **las 10** a `flows.json` con `status: pending` en el **mismo turno**. No ejecutarlas ahí: solo **catalogar y encolar** para turnos `execute_flow` posteriores.

**Alcance** (elegir uno por turno):

| Alcance | Cuándo | Qué agregar |
|---------|--------|-------------|
| **Raíz** | `discover_scope` vacío; no hay `entry` `met` con `subtree_discovered: false` | Todos los `kind: entry` nuevos visibles (p. ej. 3 menús de barra → 3 filas) |
| **Subárbol** | Hay `entry` `met` con `subtree_discovered: false` | Todos los `kind: action` hijos coherentes visibles (p. ej. 12 ítems de menú → 12 filas con mismo `parent_id`) |

Pasos:

| Paso | Tool | Buscar |
|------|------|--------|
| B1 | `get_focused_element` + `get_target_window` + `list_windows` | Ventana A vs B (modal/hijo) |
| B2 | Si subárbol: re-ejecutar entrada mínima del padre si el menú cerró | Contexto estable |
| B3 | `list_elements` / `ascii_ui_view` / `spy_tree` acotado | Items del menú, botones del modal, tabs del panel |
| B4 | Razonar por contexto | En raíz: ¿qué **entrada** falta? En subárbol: ¿qué **acciones** hay aquí? |

Reglas:

- **Raíz:** cada menú/tab/modo **nuevo** → un `entry` en la misma pasada; **no** especular items internos sin abrir.
- **Subárbol:** cada affordance accionable visible → un `action` con `parent_id`; dedupe por `discovery_signals` / título.
- Asignar `id` secuencial (`F-08`…`F-17`) y `priority` entre hermanos (orden visual o relevancia).
- Al terminar el barrido → `subtree_discovered: true` en el `entry` padre (subárbol) o marcar scope cerrado.
- `cycle.last_mode = discover_flows`; `cycle.last_discover_enqueued = N` (cantidad agregada este turno).
- Si `N === 0` → `discover_passes_without_new++`.

**Evidence (discover):**

```json
{
  "mode": "discover_flows",
  "scope": "subtree:F-05",
  "observe": "list_elements depth=3, MenuItem x12",
  "act": "enqueue F-06..F-17",
  "verify": "flows.json pending +12",
  "flows_added": ["F-06", "F-07", "..."],
  "timing_ms": 1200
}
```

---

## Regla de alternancia (intercalado)

Leer `cycle.last_mode` en `flows.json`:

| `last_mode` | Siguiente turno |
|-------------|-----------------|
| `null`, `autodetect`, `discover_flows` | **A** `execute_flow` si hay `pending`/`exploring`; si no, **B** `discover_flows` |
| `execute_flow` | **B** `discover_flows` (siempre — análisis de ventana) |

Tras `autodetect`: si `flows` está vacío → **B** obligatorio antes del primer **A**.

### Saturación de descubrimiento

Si `discover_passes_without_new >= 3` y no hay flujos `pending`:

- Priorizar cerrar `partial` / `blocked`, o
- Marcar cobertura suficiente en `lab_apps.{app}.flows_progress` y pasar a gate `perfect`.

---

## Otras fases

| Fase | Cuándo |
|------|--------|
| `discovery` (mapa UIA) | Durante `execute_flow` o primer `discover_flows` → `element-map.md` + repo si estable |
| `safety` | Solo si el usuario declaró restricciones → `safety.yaml` |
| `close` | `set_target_window('')`, resumen de flujos `met` vs total |

Cada paso → `evidence.jsonl` con `mode`, `flow_id` (si execute), `flows_added` (si discover), `timing_ms`.

---

## Estadísticas de cobertura MCP (`mcp-usage.jsonl`)

Objetivo: saber **qué parte del MCP** se ejercitó con este lab (tools, roles UIA, patterns, métodos map_*) y **qué quedó sin usar**.

### Catálogo universo

Generado desde código + mapa UIA MS:

```powershell
python scripts/build_mcp_capability_catalog.py
```

Salida: `lab-apps/mcp-capability-catalog.json`

| Dimensión | Qué mide el universo |
|-----------|----------------------|
| `mcp_tools` | Tools registradas en el servidor (ver `mcp-capability-catalog.json`; rebuild si cambió el servidor) |
| `uia_controls` | Tipos de control en `uia_control_map.json` |
| `uia_patterns_ms` | Patterns UIA (Invoke, Value, Toggle, …) |
| `act_methods` | IDs `map_*` (estrategias por control) |
| `act_bindings` | Tuplas (control, act_method, tool) |

### Registro por invocación

Cada llamada MCP durante lab → **una línea** en `runs/{active_run}/mcp-usage.jsonl`  
(plantilla: `lab-apps/mcp-usage.template.jsonl`):

```json
{
  "ts": "...",
  "tool": "invoke_element",
  "flow_id": "F-03",
  "mode": "execute_flow",
  "uia_role": "MenuItem",
  "uia_control": "MenuItem",
  "uia_pattern": "Invoke",
  "act_method": "map_invoke",
  "interacted": true,
  "outcome": "ok",
  "timing_ms": 520
}
```

| Campo | Cuándo |
|-------|--------|
| `interacted: false` | Solo lectura (`list_elements`, `spy_tree` en discover) — cuenta como **visto** |
| `interacted: true` | ACT en OBS→ACT→VERIFY — cuenta como **interactuado** |
| `act_method` | Si aplica según `discover_control_interaction` / control-catalog |

En `discover_flows`, registrar al menos las tools de observación y los **roles vistos** (batch en una o varias líneas).

### Cobertura e informe — **incremental (cada turno)**

No esperar al final de la corrida. **Después de cada turno lab:**

1. Append a `mcp-usage.jsonl` (cada tool MCP del turno).
2. Append a `improvements.jsonl` si hubo fix MCP.
3. Regenerar `coverage.json` + `lab-summary.md` (métricas acumuladas desde el inicio de la corrida).
4. Actualizar `state.json` → `lab_apps.{app}.coverage`.

El hook `stop` / `sessionStart` ejecuta el paso 3–4 automáticamente si `active_lab` está seteado.  
También manual:

```powershell
python scripts/lab_coverage_report.py
```

| Archivo | Se actualiza |
|---------|----------------|
| `mcp-usage.jsonl` | **Cada turno** (append) |
| `improvements.jsonl` | **Cada fix** (append) |
| `coverage.json` | **Cada turno** (regenerado completo desde jsonl) |
| `lab-summary.md` | **Cada turno** (mismo criterio) |
| `state.json` `lab_apps.*.coverage` | **Cada turno** (snapshot de métricas) |

Ejemplo tras 50 ciclos: `lab-summary.md` ya muestra 50 acumulados de tools usadas, gaps actuales y lista de mejoras — no hace falta «cerrar» la corrida para ver progreso.

Ejemplo de lectura: *«Llevamos 34/111 tools (30%). Faltan `read_table`, … Mejoras: 5 registros.»*

### Diff vs corrida anterior (misma app)

```powershell
python scripts/lab_coverage_diff.py
```

Genera `coverage-diff.json` + `coverage-diff.md` (tools nuevas, Δ %). También se intenta en cada actualización incremental del hook.

---

## Registro de mejoras MCP (`improvements.jsonl`)

Cada cambio al MCP motivado por la corrida → línea en `runs/{active_run}/improvements.jsonl`  
(plantilla: `lab-apps/improvements.template.jsonl`):

```json
{
  "ts": "...",
  "kind": "mcp_code",
  "summary": "Descripción breve del fix",
  "files": ["mcp-servers/awdui-server/..."],
  "tests": ["tests/test_....py"],
  "benefit": "Antes/después medible o capacidad nueva",
  "evidence": "pytest ... OK",
  "mcp_improvement_ref": "_MCP_IMPROVEMENT/...",
  "flow_id": "F-01",
  "blocker_resolved": "find_element slow"
}
```

| `kind` | Ejemplo |
|--------|---------|
| `mcp_code` | Fix en servidor |
| `mcp_tool` | Nueva tool o parámetro |
| `test` | Test que fija regresión |
| `blocker_resolved` | Desbloqueo de corrida |
| `doc` | MCP_TOOLS_REFERENCE actualizado |

El informe `lab-summary.md` agrega sección **Mejoras MCP durante la corrida** con resumen y beneficio declarado — para evaluar si los ciclos valieron la pena.

**Regla:** cualquier cambio bajo `mcp-servers/awdui-server/` durante una corrida lab → **obligatorio** append en `improvements.jsonl` (aunque el hook no lo detecte).

---

## Matriz en `state.json`

```json
"lab_apps": {
  "Calculadora": {
    "perfect": false,
    "flows_progress": { ... },
    "coverage": {
      "last_report": "runs/calc-2026/coverage.json",
      "mcp_tools_pct": 39.1,
      "uia_controls_seen_pct": 29.3,
      "updated_at": "2026-09-08T..."
    },
    "matrix": {
      "autodetect": { "status": "met" },
      "flows_catalog": { "status": "partial" }
    }
  }
}
```

---

## Repositorio de objetos (memoria entre sesiones)

Ver [object-repository.md](patterns/object-repository.md).

| Momento | Acción |
|---------|--------|
| Control estable identificado | `repo_capture` + `repo_path` en `element-map` / `flows.json` |
| Antes de `repo_find` / `repo_action` | `repo_hints` → incluir en narración «Voy a» |
| Tras workaround o verify especial | `repo_hints_set(..., append=true)` |
| Cierre de turno lab | Hook escribe `repo-snapshot.json` |

**Prohibido** cerrar un flujo `met` con workaround obligatorio sin línea en `agent_hints` del objeto tocado.

Gate `perfect`: todos los flujos **seed** en `met` (o `cancelled` con motivo), cobertura razonable de descubiertos, evidencia agentica, sin workarounds obligatorios.

### Checklist antes de append en `flows.json`

1. ¿`id` único y secuencial?
2. ¿`kind` correcto (`entry` en raíz / `action` solo con `parent_id`)?
3. ¿Padre `entry` en `met` antes de **ejecutar** hijos `action`? (encolar seeds con padre `pending` → aviso, no error)
4. ¿Sin duplicar `discovery_signals` / título?
5. Tras editar → `python scripts/validate_flows.py runs/{active_run}/flows.json`

### Gate `lab_apps.{app}.perfect` (medible — `validate_perfect_gate.py`)

| ID | Check | Criterio |
|----|-------|----------|
| G1 | Seeds | Todos `met` o `cancelled` con `notes` |
| G2 | Autodetect | `discovered.yaml` presente |
| G3 | Flujos | `validate_flows.py` sin errores |
| G4 | Evidencia | Cada seed `met` con ≥1 línea en `evidence.jsonl` (execute/verify) |
| G5 | Cobertura | `coverage.json` o `lab_apps.*.coverage` + usage/evidence |
| G6 | Latencia | Sin `outcome: slow`; discovery p95 ≤2000 ms; verify p95 ≤1500 ms |
| G7 | Blockers | Sin blockers globales (o scoped a esta app) en `state.json` |
| G8 | Repo snapshot | `repo-snapshot.json` presente (inventario + hints de la app) |

```powershell
python scripts/validate_perfect_gate.py          # usa active_run
python scripts/validate_perfect_gate.py --json
python scripts/validate_perfect_gate.py --apply  # solo si elegible
```

**Prohibido** `perfect: true` manual si el script devuelve BLOCKED. Tras `--apply`, completar plantilla [test-closure-evaluation.md](patterns/test-closure-evaluation.md).

| Requisito adicional | Verificar |
|-----------|-----------|
| Mejoras | Cada diff en `mcp-servers/` durante la corrida → línea en `improvements.jsonl` |
| Calidad MCP | Sin workarounds obligatorios (nivel 3 — no solo harness `met`) |
| Cierre | `coverage-diff.md` si hay corrida anterior; `repo-snapshot.json` actualizado |

---

## Restricciones de seguridad

Solo si el usuario las dice en el turno → `safety.yaml` o `lab_apps.{name}.safety`.

## Overrides opcionales

`lab-apps/overrides/{slug}.yaml` — solo si autodetect falla.

## Anti-patrones

- Lista fija de flujos en la skill o en código del servidor  
- Ejecutar muchos pasos de un flujo sin VERIFY entre medias  
- Saltar `discover_flows` tras cada `execute_flow`  
- Duplicar flujos en el catálogo  
- Pedir automation_ids al usuario para definir flujos  
- **Inventar hijos de un menú sin haber ejecutado el `entry` y escaneado el subárbol**  
- **Flujo `action` con `parent_id` cuyo padre no está `met`**  
- Mezclar en un solo flujo «abrir menú + elegir ítem + confirmar modal»  
- **Ejecutar en el turno discover** lo recién encolado (discover solo encola; execute consume la cola)  
- Limitar artificialmente a 1 flujo nuevo por discover cuando la UI expone varios candidatos válidos

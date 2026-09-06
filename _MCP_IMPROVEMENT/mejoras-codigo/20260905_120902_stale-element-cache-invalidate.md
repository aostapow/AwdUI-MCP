# Detección instancia UIA obsoleta tras relaunch

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-05 12:09:02 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | detection/orchestrator.py, detection/backends/uia_backend.py, tools/windows.py, tools/ui_automation.py |
| **Tool afectada** | invoke_element, launch_app, list_elements |
| **Tipo de gap** | entorno |
| **Nivel** | L4 |
| **Impacto** | alto |

## Resumen

**Problema:** Tras relaunch de Calculadora, `invoke_element` sobre `clearButton` falló
por instancia huérfana / control `disabled` de un árbol cacheado. El orchestrator
mantiene `_tree_cache` (TTL 5s) sin invalidar en `launch_app`, `set_target_window`
ni cambio de PID. El agente no invocó `invalidate_uia_cache` (documentada pero
fácil de omitir en flujos de relaunch).

**Solución:** (1) Auto-invalidar `_tree_cache` y cache UIA en `do_launch_app`,
`set_target_window` y cuando `list_windows` detecte PID distinto para el mismo título.
(2) **Pre-flight live con spy sidecar** en `do_invoke_element` / `spy_invoke_element`:
antes de InvokePattern, llamar `spy_inspect_element(automation_id=…)` (FlaUI attach
fresco, sin cache pywinauto). Si `found=false` o `is_enabled=false` →
`code=stale_instance`, invalidar cache, hint `launch_app` + `set_target_window`.
(3) **Health sentinel opcional:** parámetro `verify_live=true` (default UWP) o
probe automático con `clearButton` tras `launch_app` en sesiones Calculadora.
(4) Parámetro `fresh=true` en `invoke_element` / `list_elements` para saltar cache.

**Dónde:** `orchestrator.py`, `uia_backend.invoke_element`, `do_launch_app`.

## Contexto del turno

**Turno inicial (12:09):** `invoke_element` falló en `clearButton` (disabled / huérfano)
antes del relaunch; tras relaunch el inventario continuó con probes OK pero la
fricción inicial retrasó el ciclo y forzó recuperación manual.

**Turno seguimiento (12:11, post-fix dedup/screenshot):** Con `element_dedupe.py`
(64→34) y `screenshot` + `resolve_window_visual_rect` aplicados, el inventario live
avanzó (`3×7=21`, `8÷2=4`, `1,5`, `num0`). Persistió error COM por instancia
huérfana de Calculadora → `launch_app` relaunch manual. El agente no tenía señal
automática de que el árbol pywinauto estaba stale: `list_elements` mostraba
`clearButton` pero `invoke_element` fallaba (disabled / COM). `spy_inspect`
sobre `clearButton` en vivo habría revelado `is_enabled=false` o `found=false`
**antes** del invoke, evitando el ciclo de reintentos.

**Turno `calc_object_inventory_scientific` (12:13):** Tras relaunch, inventario
Científica avanzó (48 botones, π/e/abs OK). `clearButton` respondió pero con
**700–1000 ms** (vs ~242 ms en Estándar) — posible reintento spy+pywinauto sobre
árbol grande o instancia degradada sin invalidar cache. Refuerza necesidad de
`spy_verify_live` pre-flight: si `is_enabled=false` o PID mismatch → `stale_instance`
inmediato en lugar de invoke lento que parece éxito tardío. `trigButton`/`funcButton`
resueltos en turno 12:16 vía TogglePattern (no ExpandCollapse).

**Turno post-TogglePattern (12:16):** Fix `ActivateElement` + `uia_backend` invoke
chain; flyouts trig/func OK (`sin(0)=0`, 58 botones); `test_spy_invoke_selection.py`
6 passed; inventario Científica **met**. **Único blocker persistente:** instancia
Calculadora huérfana (`clearButton` disabled / COM) tras sesiones largas o relaunch
manual — agente debe `launch_app` + `set_target_window` sin señal `stale_instance`.
Prioridad **alta** para desbloquear `calc_object_inventory_graphing` y
`calculator_perfect`.

**Turno `calc_object_inventory_graphing` (12:19):** Inventario Graficar avanzó
(SelectionItem 302 ms; zoomIn 289 ms → eje ±9.41 vía `GraphingControl.name`;
ecuación `xButton`+`submitButton` 346 ms). **Graphing partial** por controles
pendientes (`zoomOut`, `GraphSettingsButton`, `ActiveTracing`, `yButton`,
`inequalityButton`) y verificación post-submit oculta por vista ecuación — no por
fallo UIA en zoom. **Blocker igual:** sesión stale interrumpe relaunch manual antes
de cerrar inventario; `clearButton` disabled sin `code=stale_instance`. Refuerza
prioridad **alta** del pre-flight `spy_verify_live` + invalidación post-`launch_app`.

## Cambio propuesto (pseudodiff)

```python
# orchestrator.py
def invalidate_tree_cache(window_title: str | None = None) -> int:
    global _tree_cache
    if not window_title:
        n = len(_tree_cache)
        _tree_cache.clear()
        return n
    keys = [k for k in _tree_cache if k.startswith(f"{window_title}|")]
    for k in keys:
        del _tree_cache[k]
    return len(keys)
```

```python
# windows.py do_launch_app — tras Popen exitoso
from detection.orchestrator import get_orchestrator
get_orchestrator().invalidate_tree_cache()
```

```python
# spy_bridge.py — nuevo helper
def spy_verify_live(
    automation_id: str,
    window_title: Optional[str] = None,
    require_enabled: bool = True,
) -> dict:
    hit = spy_inspect_element(automation_id=automation_id, window_title=window_title)
    if not hit.get("found"):
        return {"live": False, "code": "stale_instance", "reason": "not_found"}
    props = hit.get("properties") or {}
    enabled = bool(props.get("is_enabled", True))
    pid = int(props.get("process_id", 0) or 0)
    if require_enabled and not enabled:
        return {"live": False, "code": "stale_instance", "reason": "disabled",
                "process_id": pid, "automation_id": automation_id}
    return {"live": True, "process_id": pid, "enabled": enabled, "properties": props}
```

```python
# ui_automation.py do_invoke_element — antes de spy_invoke_element / pywinauto
from tools.spy_bridge import spy_verify_live, spy_available
if spy_available() and automation_id:
    live = spy_verify_live(automation_id, window_title)
    if not live.get("live"):
        from tools.wait_tools import do_invalidate_uia_cache
        do_invalidate_uia_cache()
        return {
            "success": False,
            "error": f"Stale UIA instance ({live.get('reason')})",
            "code": live.get("code", "stale_instance"),
            "hint": "launch_app + set_target_window; re-list_elements fresh",
            "probe": automation_id,
        }
```

```python
# do_launch_app — post-relaunch health probe (Calculadora / UWP)
_HEALTH_SENTINELS = {"Calculadora": "clearButton", "Calculator": "clearButton"}

def _post_launch_health_probe(title: str) -> dict:
    aid = _HEALTH_SENTINELS.get(title.split()[0])  # or detect_framework
    if not aid:
        return {"skipped": True}
    from tools.spy_bridge import spy_verify_live
    return spy_verify_live(aid, title, require_enabled=True)
```

```python
# uia_backend.invoke_element — fallback pywinauto path
if not raw:
    return {"success": False, "error": "Element not found", "code": "stale_element",
            "hint": "Call invalidate_uia_cache or spy_inspect before invoke"}
```

```python
# ui_automation.py list_elements — parámetro opcional
fresh: bool = False  # skip orchestrator cache when True
```

## Verificación de duplicados

- Propuesta única sobre stale post-relaunch (ampliada turno 12:11 con spy pre-flight).
- `invalidate_uia_cache` en docs — esta propuesta **conecta** la tool con
  invalidación automática; no la reemplaza.
- Distinto de `element_dedupe` (aplicado turno 12:11) y `screenshot visual_rect`
  (aplicado turno 12:11): esos fixes no resuelven COM/huérfano.

## Test de abstracción

Aplica a cualquier app relanzada (AST, diálogos modales cerrados/reabiertos,
Calculadora reiniciada) — no sintoma puntual.

## Criterio de aceptación

- [ ] `tests/test_uia_tree_cache.py` (nuevo): cache hit → launch_app → cache miss.
- [ ] `tests/test_stale_instance_probe.py`: mock `spy_inspect` disabled →
      `invoke_element` devuelve `code=stale_instance` sin llamar InvokePattern.
- [ ] `spy_verify_live("clearButton")` con proceso huérfano → `live=false`, cache invalidado.
- [ ] `invoke_element` con `automation_id` de instancia previa devuelve `code=stale_instance`.
- [ ] `launch_app` invalida cache + health probe `clearButton` enabled para Calculadora.
- [ ] Documentar en `MCP_TOOLS_REFERENCE.md` flujo post-relaunch y `verify_live`.

## Beneficios futuros

- Menos reintentos ciegos tras `launch_app` / crash recovery.
- Errores accionables para el agente (hint explícito vs "Element not found").
- Ciclo Calculadora más estable en inventarios largos con relaunch intermedio.

## Evidencia adicional — turno `calculator_perfect_eval` (2026-09-05 12:39)

**Implementación parcial aplicada (mismo turno, MCP reiniciado):**
- `stale_instance_probe` + `invalidate_tree_cache` en `do_launch_app`.
- **pytest 9 passed** (suite stale_instance / cache invalidation).
- Relaunch manual + `spy_inspect(clearButton)` → `is_enabled=true` antes de invokes Estándar.

**Mitigación observada:** blocker huérfana marcado `blockers_mitigated` en `state.json`;
flujo Estándar 12×8=96 sin reintentos COM tras relaunch.

**Pendiente de esta propuesta (no archivar aún):**
- [ ] Pre-flight `spy_verify_live` automático en `do_invoke_element` (agente aún invoca
      `spy_inspect` manualmente tras relaunch).
- [ ] Parámetro `fresh=true` en `list_elements` / `invoke_element`.
- [ ] Health sentinel post-`launch_app` sin intervención manual.
- [ ] `code=stale_instance` accionable cuando probe falla (vs relaunch ad-hoc).

**Mantenedor:** marcar criterios parciales aplicados; archivar solo cuando pre-flight
invoke + health sentinel estén cubiertos por tests live.

## Evidencia adicional — turno `calculator_exhaustive_act_verify` (2026-09-05 16:48)

**Observado:** Primera pasada `10-3=` verificó display **«Se muestra 63»** (expresión
previa `9×7` en PID **24468**) mientras `spy_inspect` reportaba PID **2072** distinto
al `launch_app` reciente. `invoke_element` sobre `minusButton`/`equalButton` no falló
con `code=stale_instance` — el árbol UIA respondió pero leyó **CalculatorResults** de
instancia huérfana. Relaunch manual + `set_target_window` → verificación correcta
**«Se muestra 7»** (PID **6988** consistente).

**Skill:** `calculator-lab.md` ya documenta protocolo PID mismatch → relaunch antes
de verificar display (turno actual).

**Refuerza pendientes de esta propuesta:**
- [ ] Health sentinel post-`launch_app`: comparar `process_id` de `spy_inspect(clearButton)`
      o `CalculatorResults` vs PID de sesión **antes** de aceptar texto de display.
- [ ] Pre-flight en lectura de verificación (no solo en `invoke_element`): si PID diverge,
      devolver `code=stale_instance` + hint relaunch sin ejecutar act.
- [ ] `get_element_properties` / lectura display con `verify_live` automático en UWP.

## Evidencia adicional — turno `calculator_exhaustive_act_verify` cierre (2026-09-05 13:02)

**Estándar (post-recuperación):** `divideButton` 15÷3=5, `multiplyButton` 4×5=20,
`HistoryButton` flyout + `LightDismiss` verificados; screenshot `awdui_1788624105130_1.png`.

**Científica (misma sesión, pre/post disconnect):** `cosButton`/`tanButton` —
`invoke_element` devolvió éxito pero `CalculatorExpression` leyó **«0=»** sin nombre de
función; `sinButton` devolvió **`code=stale_instance`** explícito (pre-flight probe).

**Entorno:** conexión MCP cerrada a mitad de sesión; reinicio `AWDUI_RESTART=1788624058`.
Tras reconexión el agente retomó Estándar OK pero Científica quedó con lecturas display
inconsistentes y `sinButton` stale.

**Refuerza pendientes:**
- [ ] `_stale_instance_probe` en **lectura** de `CalculatorExpression` / `CalculatorResults`
      (no solo en `invoke_element`) — cos/tan «OK» con expresión huérfana es el mismo gap PID.
- [ ] Tras `Connection closed` / restart MCP: health sentinel obligatorio
      (`check_version` → `launch_app` calc → `spy_inspect(clearButton).process_id`) antes
      de continuar inventario multi-modo.
- [ ] `sinButton` stale tras disconnect sugiere invalidar cache UIA también en
      reconexión MCP (no solo `launch_app`).

## Evidencia adicional — turno cierre trig (2026-09-05 13:05)

**Escenario concreto:** tras `clearButton` con flyout trig **abierto** (`trigButton` On),
`invoke_element(sinButton)` devolvió `code=stale_instance` mientras `cosButton`/`tanButton`
respondieron OK en la misma pasada. Sugiere invalidación selectiva de hijos flyout tras
clear, no solo post-`launch_app`.

**Recovery documentado en skill:** `launch_app calc` + repetir sin `clearButton` innecesario
entre funciones del mismo flyout.

**Refuerza:** pre-flight `spy_verify_live` en invoke + invalidar cache al detectar
`stale_instance` en cualquier botón flyout tras mutación de display (`clearButton`).

## Evidencia adicional — turno exhaustive sec/csc/cot (2026-09-05 13:06)

**Trigger stale confirmado:** mutación display vía `equalButton` (no solo `clearButton`) invalida
flyout trig para encadenamiento — sec/csc/cot **solo pasaron** con `launch_app calc` entre cada
función.

**Workaround skill (temporal):** `calculator-lab.md` documenta relaunch por función; no sustituye
invalidación automática post-`equalButton` en MCP.

**Refuerza pendientes:**
- [ ] Invalidar `_tree_cache` tras `invoke_element(equalButton)` o lectura display que cambia
      `CalculatorResults` (además de post-`launch_app`).
- [ ] Health probe tras `equalButton` en sesiones Científica multi-función: si siguiente
      `spy_verify_live(secButton)` → stale, auto-invalidate + hint relaunch sin fallo opaco.

## Evidencia adicional — turno trig flyout 17/17 (2026-09-05 20:42)

**Sesión:** `reuse=true` PID **4428**; Alt+2 Científica; flyout trig **17/17** completo
(sin/cos/tan + sec/csc/cot + inverse invsec/invcsc/invcot → resultado **0** verificado).

**Stale post-`equalButton`:** tras encadenar funciones trig, recovery con `reuse=true` +
reabrir `trigButton` (sin `replace=true`) — workaround skill funciona pero añade pasos
manuales y latencia (`find` ⚠ SLOW en re-probe del flyout).

**Contraste turno 13:06:** antes requería `launch_app` por función; aquí `reuse` + trig
reopen alcanzó 17/17 — confirma que invalidación selectiva post-`equalButton` reduciría
recovery sin relaunch completo.

**Refuerza pendientes:**
- [ ] Invalidar cache hijos flyout tras `equalButton` (no solo tras `clearButton`).
- [ ] Auto-reopen `trigButton` hint cuando `spy_verify_live(sinButton)` → stale y
      `trigButton` state Off tras equal en sesión Científica.

## Evidencia adicional — turno Graphing exhaustive (2026-09-05 20:45)

**Escenario:** tras `SwitchModeToggleButton` (vista ecuación On), `invoke_element(yButton)`
respondió con árbol stale / fallo de invoke (521 ms) mientras `xButton` y `submitButton`
en la misma vista funcionaron en pasadas previas.

**Patrón:** mutación de vista Graficar (`SwitchModeToggleButton`, `inequalityButton` Toggle)
invalida referencias cacheadas de botones hermanos en `EquationInputList` — análogo a flyout
trig post-`equalButton`.

**Workaround skill (consolidar en `121900`):** tras cada `SwitchModeToggleButton` o toggle de
`inequalityButton`, `list_elements(fresh=true)` o `spy_inspect` del botón objetivo antes de invoke.

**Refuerza pendientes:**
- [ ] Invalidar `_tree_cache` tras `invoke_element(SwitchModeToggleButton)` en sesiones UWP
      con paneles mutuamente excluyentes (Graficar ecuación ↔ gráfico).
- [ ] Pre-flight `spy_verify_live` en `yButton`/`xButton` tras toggle de vista ecuación.

## Evidencia adicional — turno Graphing submit EquationButton (2026-09-05 20:47)

**Escenario:** `xButton` + `submitButton` invoke OK (497 ms); screenshot muestra línea `y=x`
en rejilla. `GraphingControl.name` **permanece** `0 ecuaciones` — no es solo vista ecuación
oculta: el conteo en `name` del Custom **no se actualiza** vía árbol cacheado.

**Señal fiable:** `EquationButton.name` → **«Ocultar ecuación 1»** inmediatamente tras submit
(sin `graphViewButton`, sin relaunch). Misma clase de stale que `CalculatorResults` post-equal
pero en control Graficar.

**Workaround skill (consolidar en `121900`):** verify submit con `spy_inspect(EquationButton)`,
no `GraphingControl` conteo.

**Refuerza pendientes:**
- [ ] `get_element_properties` / lectura `name` con `verify_live` o `fresh=true` cuando
      `GraphingControl` conteo contradice `EquationButton` o screenshot.
- [ ] Hint en respuesta: «GraphingControl equation count may be stale; use EquationButton.name».
- [ ] Invalidar cache tras `submitButton` invoke en modo Graficar (análogo post-`equalButton`).

## Evidencia adicional — turno Date exhaustive (2026-09-05 21:03)

**Escenario:** Modo Fecha completo (DateDiff 4 días ✓; Sumar/restar días ✓). Tras
`SubtractOption` + `DaysValue` 4 → `DateResultLabel` «viernes 28 agosto 2026» OK, retry sobre
`DateDiff_ToDate` devolvió **`stale_instance`**; recovery con `launch_app reuse=true` sin
`replace=true`.

**Patrón:** mutación de sub-modo (`AddOption` ↔ `SubtractOption`, cambio de panel
`DateDiff_*` ↔ `AddDays_*`) invalida referencias cacheadas de pickers de fecha — análogo a
flyout trig post-`equalButton` y Graficar post-`SwitchModeToggleButton`.

**Workaround del turno:** `reuse=true` + re-`set_target_window` suficiente; no bloqueó
verificación final pero añadió paso de recovery.

**Refuerza pendientes:**
- [ ] Invalidar `_tree_cache` tras `SelectionItem` en `AddOption`/`SubtractOption` o cambio
      visible en `DateCalculationOption` hijos.
- [ ] Pre-flight `spy_verify_live` en `DateDiff_ToDate` / `DateDiff_FromDate` tras cambio de
      sub-modo Sumar/restar ↔ Diferencia.
- [ ] Hint: «Date picker stale after mode switch; reopen picker or invalidate cache».

## Evidencia adicional — turno Settings exhaustive (2026-09-05 21:10)

**Escenario:** sesión con PID **4428** reutilizado (`reuse=true`); múltiples fallos en
Settings antes de `launch_app(path='calc.exe', replace=true)` → PID **27880** consistente.

**Patrón:** misma instancia stale que turnos trig/Graphing/Date — `reuse=true` prolonga
árbol huérfano hasta `replace=true` cierra duplicados y abre instancia fresca.

**Workaround del turno:** `replace=true` desbloqueó Settings exhaustive completo
(`SettingsItem` 549 ms, theme radios, About, Feedback, BackButton).

**Refuerza pendientes:**
- [ ] `launch_app` con `reuse=true` debe comparar PID activo vs último probe; si probe
      falla N veces → auto-sugerir `replace=true` en hint (no solo `stale_instance` opaco).
- [ ] Health sentinel al **inicio** de sub-flujos largos (Settings tras Date exhaustive):
      `spy_inspect(clearButton).process_id` vs ventana target antes de `SettingsItem`.
- [ ] Documentar en `calculator-lab.md`: tras ≥2 fallos invoke/find en misma sesión,
      escalar a `replace=true` sin reintentar `reuse=true`.

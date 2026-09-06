# Calculadora Científica — verificar unarios por CalculatorResults

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | aplicada |
| **Fecha** | 2026-09-05 13:02:01 |
| **Skill objetivo** | awdui-flow-exploration/patterns/calculator-lab.md |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Impacto** | medio |
| **MCP versión** | v0.2.1 |

## Resumen

**Problema:** Tras `invoke_element` en `cosButton`/`tanButton`, el agente verificó solo
`CalculatorExpression` y obtuvo **«0=»** sin función, declarando fallo ambiguo. El harness
exige «invoke + verify display» pero no prioriza **qué** control leer ni el protocolo
unario (operand → función → resultado). `CalculatorExpression` puede quedar desfasado o
leer instancia stale mientras `invoke_element` reporta éxito.

**Solución:** Añadir en `calculator-lab.md` sección «Funciones unarias Científica»:

1. **Pre:** `clearButton` → operando (ej. `num0`) → capturar `spy_inspect(CalculatorResults).name`.
2. **Act:** `invoke_element` en `sinButton`/`cosButton`/… (flyout trig abierto si aplica).
3. **Verify primario:** `CalculatorResults` — debe cambiar (ej. `cos(0)` → «1»).
4. **Verify secundario:** `CalculatorExpression` — opcional; si invoke OK pero expression
   sin token de función y results sin cambio → **stale/PID mismatch**, no «función rota».
5. **Post MCP disconnect:** `check_version` → `launch_app` calc → confirmar PID único antes
   de modo Científica.

**Dónde:** `patterns/calculator-lab.md` — subsección tras «Chrome memoria».

## Contexto del turno

`calculator_exhaustive_act_verify`: Estándar OK; Científica cos/tan invoke OK, expression
«0=»; sinButton stale_instance; MCP restart mid-session.

## Texto propuesto

### Funciones unarias (modo Científica)

| Paso | Tool | Criterio |
|------|------|----------|
| 1 | `spy_inspect(CalculatorResults)` | Anotar `name` / valor mostrado |
| 2 | `invoke_element` función | `success` + `method` Invoke/Toggle |
| 3 | `spy_inspect(CalculatorResults)` | **Debe diferir** del paso 1 |
| 4 | `spy_inspect(CalculatorExpression)` | Opcional; token `sin`/`cos`/… si visible |

**Anti-patrón:** Declarar función verificada solo por `CalculatorExpression` cuando
`CalculatorResults` no cambió — suele ser lectura stale (ver propuesta código display-verify).

**Tras `Connection closed` MCP:** no continuar inventario multi-modo sin relaunch Calculadora
y PID consistente en `clearButton` + display.

## Verificación de duplicados

- Complementa `121301` (flyout Toggle) — cubre verificación post-invoke, no apertura flyout.
- Complementa `120902` / `130200` (código stale read) — esta skill guía al agente mientras
  el código no expone `verify_display` automático.

## Criterio de aceptación

- [ ] Texto sin coords del turno
- [ ] Prioriza `CalculatorResults` sobre `CalculatorExpression`
- [ ] Menciona recovery post-disconnect MCP sin nombrar `AWDUI_RESTART`

## Beneficios futuros

- Menos falsos negativos «función no aplicada» en inventario Científica.
- Alinea harness sección C con protocolo OBS→ACT→VERIFY concreto.

## Evidencia adicional — turno cierre trig (2026-09-05 13:05)

**Aplicado en turno:** `calculator-lab.md` sección «Científica — flyout trigonometría» (líneas 38–49)
incorpora protocolo definitivo:

- Unary **sin** `num0Button` — cos/tan/sin usan argumento 0 por defecto.
- Verify expression: «grados de coseno (0)» / «grados de tangente (0)» antes de `equalButton`.
- Resultados: cos(0)=1, tan(0)=0, sin(0)=0.
- Anti-patrón `cos` → `0` → `=` documentado (falso negativo «0=» era **ejecución**, no gap MCP).
- Stale `sinButton` tras `clearButton` con flyout abierto — recovery `launch_app` sin clear entre funcs.

Screenshot: `awdui_1788624205316_8.png`.

**Corrección vs texto propuesto arriba:** eliminar paso «operando (ej. num0)» del pre-flight;
el protocolo correcto es `trigButton` On → `invoke_element` función → verify expression → `equalButton`.

**Mantenedor:** marcar `Estado: aplicada` y archivar con `scripts/archive-mcp-improvements.ps1`.

## Evidencia adicional — turno exhaustive sec/csc/cot (2026-09-05 13:06)

**Verificado live:** `secButton`→`equalButton` → sec(0)=**1**; `cscButton`→`equalButton` → csc(0)=**0**;
`cotButton`→`equalButton` → cot(0)=**0**. Patrón **func→=** sin `num0Button` (mismo que sin/cos/tan).

**Recovery stale:** `launch_app calc` **por cada función** tras `equalButton` evitó `stale_instance` al
encadenar sec/csc/cot — confirmado en turno (relaunch individual entre funciones).

**Skill actualizada:** `calculator-lab.md` línea 49 — nota stale ampliada con sec/csc/cot + relaunch
por función.

**Screenshots:** `awdui_1788624294584_10.png` (sec), `awdui_1788624374612_1.png` (cot).

**Pendiente menor en skill (L1, no nueva propuesta):** línea 45 del protocolo aún ejemplifica solo
sin/cos/tan en expression/results — extender a sec/csc/cot al archivar (secante/cosecante/cotangente).

**Recomendación:** `Estado: aplicada` — protocolo unary + anti-patrón + stale relaunch documentados y
validados en 6 funciones trig (sin/cos/tan/sec/csc/cot).

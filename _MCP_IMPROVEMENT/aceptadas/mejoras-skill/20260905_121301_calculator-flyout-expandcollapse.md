# Calculadora Científica — flyouts trig/func vía TogglePattern

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | aplicada |
| **Fecha** | 2026-09-05 12:13:01 |
| **Skill objetivo** | awdui-flow-exploration/patterns/calculator-lab.md |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Impacto** | medio |

## Resumen

**Problema:** En inventario Científica, el agente usó `invoke_element` en `trigButton` y
`funcButton` esperando InvokePattern; UIA expone **TogglePattern** para abrir flyouts
(estado `On`/`Off`). Falló hasta fix MCP en spy + `uia_backend` (turno 12:16).

**Solución:** Añadir sección en `calculator-lab.md` (patrón cross WinUI flyout toggle):

1. `spy_inspect(automation_id=trigButton)` → confirmar `Toggle` en patterns.
2. `invoke_element` → respuesta `method: TogglePattern`; verificar `ToggleState: On`.
3. `list_elements` / `spy_tree` para hijos flyout (`sinButton`, `cosButton`, …).
4. Seleccionar función → verificar display → `invoke_element` de nuevo para cerrar flyout
   (Toggle off) o click fuera (`LightDismiss` si visible).
5. **No** usar coords salvo último recurso.

**Dónde:** `patterns/calculator-lab.md` — nueva subsección «Flyouts Científica».

## Contexto del turno

Inventario `calc_object_inventory_scientific`: 48 botones mapeados; π, e, abs(-5)
verificados. Turno 12:16: TogglePattern fix aplicado; `sin(0)=0`; 58 botones con
flyouts. **Pendiente:** texto en `calculator-lab.md` (código ya OK).

## Texto propuesto

### Flyouts modo Científica (trig / func)

| automation_id | Rol UIA | Pattern | Hijos tras toggle On |
|---------------|---------|---------|----------------------|
| `trigButton` | Button | **TogglePattern** | sin, cos, tan, sec, csc, cot, … |
| `funcButton` | Button | **TogglePattern** | rand, log, factorial, … |
| `trigShiftButton` | Button | Invoke / Toggle | panel 2ª función trig |

**Protocolo:** OBSERVAR patterns → ACTUAR `invoke_element` (Toggle) → VERIFICAR hijos + screenshot.

## Verificación de duplicados

- Complementa (no duplica) propuesta código ExpandCollapse.
- `control-catalog.md` ya cubre SplitButton genérico; esta skill es mapa estable Calculadora.

## Criterio de aceptación

- [ ] Texto sin depender de coords del turno
- [ ] Enlaza a `invoke_element` cascada post-fix
- [ ] Aplicable como plantilla flyout WinUI en otras apps

## Beneficios futuros

- Menos reintentos ciegos en inventarios por modo.
- Agentes leen patterns antes de declarar gap en trig/func.

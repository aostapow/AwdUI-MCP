---
name: mcp-improvement-cycle
description: >-
  Ciclo continuo de mejora del MCP AwdUI. App de prueba: Calculadora hasta
  calculator_perfect. Evaluación solo agentica (MCP); scripts no validan
  cobertura. objective_met requiere infra + Calculadora completa.
---

# Ciclo de mejora MCP (continuo y repetible)

> **Skill principal:** [awdui-mcp-objective/SKILL.md](../awdui-mcp-objective/SKILL.md)  
> **Calculadora (detalle):** [calculator-mcp-harness/SKILL.md](../calculator-mcp-harness/SKILL.md)  
> **Hooks:** `.cursor/hooks.json` (`stop` reintenta si `objective_met` es false)

## Objetivo (no negociable)

**MCP confiable + Calculadora UWP probada de punta a punta solo con tools MCP.**

- **Entregable código:** `mcp-servers/awdui-server/` + tests unitarios + docs
- **Entregable evidencia:** `state.json` (`calculator_matrix`, `calculator_evidence`, screenshots)
- **App de prueba:** solo Calculadora hasta `calculator_perfect: true`
- **Prohibido como evaluación:** scripts Python, pytest integration, gates batch

## Cuándo termina el ciclo

```text
objective_met = true  ⇔  mcp_infra_ready  ∧  calculator_perfect
```

Ambos deben tener evidencia agentica documentada. Ver skills citadas.

## Un ciclo = una iteración

```
1. LEER state.json + calculator-mcp-harness SKILL
2. OBSERVAR Calculadora (MCP) — un foco de la matriz
3. Si gap MCP → un fix mínimo en servidor
4. pytest unitario del módulo tocado
5. VERIFICAR agentico: UIA + screenshot en hito
6. ACTUALIZAR calculator_matrix, calculator_evidence, criteria_status
7. ¿calculator_perfect? ¿objective_met? → siguiente ciclo si false
```

## Reglas del ciclo

| Regla | Detalle |
|-------|---------|
| Evaluación agentica | Solo tools MCP; descubrimiento **completo** por pantalla, no mínimo |
| Pausa usuario | `scripts/pause-mcp-cycle.ps1` — hooks y subagentes no reinician |
| Mejora de skills | Cada turno con fricción → actualizar skill o pattern |
| Sin scripts para cobertura | No `run_calculator_coverage`, no `explore_calculator*` como prueba |
| Sin observación no hay acción | `list_elements` vacío → fix observación |
| Sin verificación no hay “done” | UIA + screenshot en hitos |
| Una app hasta perfecta | No AST hasta `calculator_perfect` |
| Un fix por ciclo | No mezclar muchos cambios MCP |

## Archivos de estado

| Archivo | Rol |
|---------|-----|
| `.cursor/mcp-improvement-cycle/state.json` | Objetivo, matriz, evidencia, flags |
| `.cursor/mcp-improvement-cycle/cycle.log` | Auditoría por ciclo |

## Controlador de ciclo (subagente)

Al cerrar turno con trabajo MCP o Calculadora: lanzar `mcp-cycle-controller` en background. Debe validar **honestamente** `calculator_perfect`, no solo infra pasada.

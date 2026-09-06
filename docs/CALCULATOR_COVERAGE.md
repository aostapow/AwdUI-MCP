# Calculator — cobertura agentica (sin scripts)

> **Fuente de verdad:** `.cursor/skills/calculator-mcp-harness/SKILL.md`  
> **Estado:** `.cursor/mcp-improvement-cycle/state.json` (`calculator_matrix`, `calculator_evidence`)

## Objetivo

Cubrir **toda** la Calculadora UWP con el **agente** y tools MCP — no con scripts Python.

## Evaluación

| Permitido | Prohibido como prueba de la app |
|-----------|----------------------------------|
| Tools MCP paso a paso | `explore_calculator_modes.py` |
| `screenshot` en hitos | `run_calculator_coverage.py` |
| `calculator_evidence` en state.json | pytest integration como gate de cierre |
| pytest **unitario** del servidor MCP | Scripts batch con `pyautogui` |

## Mapa UIA (referencia)

### NavView (`TogglePaneButton`)

`Standard`, `Scientific`, `Graphing`, `Programmer`, `Date`, `Currency`, `Volume`, `Length`, `SettingsItem`

### Chrome

`HistoryButton`, `MemoryButton`, `MemPlus`, `MemRecall`, `ClearMemoryButton`, `Header`, `CalculatorResults`

## Matriz y evidencia

El agente mantiene progreso en `state.json` — no en JSON generado por scripts.

Ver skill para criterios de `calculator_perfect` y protocolo OBS→ACT→VERIFY.

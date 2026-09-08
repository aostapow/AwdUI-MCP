# Evaluación de cierre — harness vs MCP perfecto

> **Obligatorio** al dar por finalizadas tareas de prueba (flujo NP-XX, lote harness, sesión,
> o al marcar `*_perfect` / `objective_met` en `state.json`).

## Cuándo entregar este resumen

| Evento | Entregar evaluación de cierre |
|--------|-------------------------------|
| Último flujo de un lote (ej. NP-30) | **Sí** — además del resumen del flujo |
| Marcar `lab_apps.{id}.perfect` | **Sí** — aunque la matriz esté 100% `met` |
| Marcar `objective_met: true` | **Sí** — obligatorio antes de declarar ciclo completo |
| Usuario pregunta «¿está perfecto?» | **Sí** — respuesta honesta con esta plantilla |
| Un solo flujo intermedio (NP-12 en curso) | No — solo resumen de flujo (ver `agentic-execution.md`) |

**Prohibido** cerrar sesión de prueba solo con «30/30 met» o «objective_met true» sin la sección
**Evaluación honesta MCP** de abajo.

---

## Tres niveles de «cumplido» (no confundir)

| Nivel | Qué significa | ¿Implica MCP perfecto? |
|-------|---------------|---------------------------|
| **1 — Flujo `met`** | OBS→ACT→VERIFY del NP-XX pasó (puede usar workarounds de skill) | **No** |
| **2 — Harness `*_perfect`** | Matriz completa (ej. 30/30 NP, 9 modos Calculadora) | **No** — solo capacidad agentica con compensaciones |
| **3 — MCP calidad operativa** | Acciones simples cierran en **1 tool** sin coords manuales, verify fiable, foco teclado OK | **Sí** — objetivo real del repo |

Marcar nivel 2 **no** autoriza afirmar nivel 3. Si quedaron workarounds obligatorios documentados,
la evaluación de calidad MCP debe decir **NO está perfecto**.

---

## Señales de workaround (detectar en el turno)

Contar como workaround (no como contrato MCP definitivo):

| Señal en ejecución | Workaround típico |
|--------------------|-------------------|
| `invoke_element` / `click_element` OK pero `✗ verify failed` | Verify extra con `list_windows` / `read_element` |
| `MenuItem` visible, Invoke falla | `list_elements` → `click(x,y)` manual desde bbox |
| `send_keys` / atajo sin efecto en editor | `click_element` en editor antes de cada teclado |
| Atajo genérico falla (ej. Ctrl+A abre Abrir) | Atajo locale documentado solo en skill producto |
| `set_target_window` ambiguo multi-instancia | Título exacto con `*`, PID manual, `list_desktop_windows` |
| `list_elements` >2s por paso de menú | Evitar discovery; memorizar `automation_id` de skill |
| Modal: `automation_id` colisiona entre ventanas | `name` + `role` + `window_title` en cada find |

Cada workaround usado en la sesión → fila en la tabla de cierre.

---

## Plantilla obligatoria (chat al usuario)

Copiar/adaptar al cerrar pruebas:

```markdown
## Cierre de pruebas — evaluación honesta

### Resultado harness
| Métrica | Valor |
|---------|-------|
| Matriz | X/Y flujos `met` |
| `*_perfect` en state.json | true/false |
| Tests unitarios MCP | pytest … → passed/failed |

### Veredicto calidad MCP (nivel 3)
**¿MCP listo sin workarounds obligatorios?** NO | PARCIAL | SÍ

Si NO o PARCIAL: es normal que el harness esté `met` — el agente compensó gaps del servidor.

### Workarounds usados (harness pasó, MCP no cerró solo)
| Problema raíz | Síntoma | Workaround en sesión | Fix real (MCP/skill) | Backlog |
|---------------|---------|----------------------|----------------------|---------|
| Verify post-act no confiable | verify failed 5–17s | `list_windows` extra | verify semántico modal/editor | `_MCP_IMPROVEMENT/...` |
| … | … | … | … | … |

### Pendiente implementar y re-probar
| Prioridad | Fix | Flujos regresión sugeridos |
|-----------|-----|----------------------------|
| P1 | … | NP-25, NP-24, … |
| P2 | … | … |

### Blockers / waivers activos
- …

### Conclusión en una frase
El harness **[cumplió / no cumplió]** la matriz; la calidad MCP **[no está / está parcialmente / está]** lista
para automatización simple sin compensaciones del agente.
```

---

## Actualizar `state.json` con honestidad

Al marcar `*_perfect` o `objective_met`:

1. **`blockers`** — mantener activos los gaps de performance/verify no resueltos (ej. `list_elements` slow).
2. **`last_cycle.notes`** — una línea: «harness met con N workarounds; MCP calidad: NO perfecto».
3. **No borrar** propuestas pendientes en `_MCP_IMPROVEMENT/mejoras-*/` solo porque la matriz pasó.

Opcional (recomendado): `mcp_quality_status`: `"workarounds_required"` | `"partial"` | `"operational"`.

---

## Regla de respuesta al usuario

| Pregunta | Respuesta correcta |
|----------|-------------------|
| «¿Quedó perfecto?» | Separar harness (nivel 2) vs MCP (nivel 3). Si hubo workarounds → **no perfecto** en calidad. |
| «¿Por qué tantos workarounds?» | Tabla causa raíz → fix MCP; el harness validó skill+agente, no servidor solo. |
| «¿Puedo usar esto en producción?» | Solo si nivel 3; si solo nivel 2 → listar P1 pendientes antes. |

---

## Referencias

- Objetivo global: [SKILL.md](../SKILL.md)
- Notepad protocolo: [notepad/protocol/agentic-execution.md](../../notepad/protocol/agentic-execution.md)
- Gaps Notepad: [notepad/gaps/mcp-improvements.md](../../notepad/gaps/mcp-improvements.md)
- Regla: `.cursor/rules/awdui-test-closure.mdc`

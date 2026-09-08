# Protocolo agentico estricto — harness Notepad

> **Obligatorio** para todo turno que ejecute flujos NP-01..NP-30 o valide tools MCP contra Notepad.
> Complementa [awdui-flow-exploration/SKILL.md](../../awdui-flow-exploration/SKILL.md) Fase 6.

## Reglas duras

| # | Regla | Violación típica |
|---|-------|------------------|
| R1 | **Una tool MCP por turno de ejecución** — esperar resultado antes de la siguiente | Lanzar `send_keys` + `list_windows` + `read_element` en paralelo |
| R2 | **Anunciar en chat antes de actuar** — frase explícita: qué tool, parámetros, resultado esperado | Ejecutar tools sin narrar |
| R3 | **Verificar empíricamente cada paso** — no avanzar si la verificación falla | Asumir que Escape cerró un modal |
| R4 | **Identificar la ventana activa** tras cada paso que pueda abrir/cerrar UI | Teclado llega a `Abrir` en lugar del editor |
| R5 | **Recuperar antes de continuar** — ver [recovery.md](recovery.md) | Arreglar NP-10 mientras queda `Abrir` abierto |
| R6 | **Screenshot solo en hitos** — baseline, post-acción dudosa, cierre de flujo | Screenshot en cada paso |
| R7 | **Tabla de resumen al cerrar cada flujo** — ver plantilla abajo | Terminar sin reportar avance |

## Ciclo por paso (chat + MCP)

Para **cada paso numerado** del flujo:

```
PASO N — [nombre corto]

Voy a: <tool>(<params>) porque <objetivo>.

→ [ejecutar UNA tool]

Resultado: OK | FAIL | DUDOSO
Evidencia: <output literal relevante — timing, título ventana, value leído>
Si FAIL/DUDOSO:
  - Hipótesis: <por qué>
  - Diagnóstico: list_windows / get_focused_element / screenshot
  - Acción: recovery L1/L2/L3 (recovery.md) → reintentar paso N
```

**Prohibido** saltar al paso N+1 con verificación FAIL sin recovery documentado.

## Plantilla de paso (flows/*.md)

Cada flujo debe listar pasos con esta forma:

```markdown
### Paso 1 — Baseline ventanas
- **Act:** `list_windows`
- **Esperado:** solo `Bloc de notas` (+ ruido Cursor); sin `#32770` Abrir/Guardar como
- **Verify:** contar ventanas `notepad.exe`; anotar títulos
- **Si falla:** recovery L1 (cerrar modales) → L2 (focus) → L3 (kill)

### Paso 2 — ...
```

## Verificaciones aceptadas por tipo

| Tipo de paso | Verify mínima | Verify fuerte |
|--------------|---------------|---------------|
| Abrir modal | `list_windows` muestra título modal | `get_focused_element` dentro del modal |
| Cerrar modal | título **ausente** en `list_windows` | `get_focused_element` vuelve al padre |
| Escribir editor | `read_element` id=15 value contiene texto | status bar línea/col cambió |
| Menú | hijo MenuItem visible tras invoke padre | screenshot hito |
| Teclado | efecto observable (título, value, ventana) | no confiar solo en "Sent keys" |
| Watcher | `get_notifications` evento WINDOW con título | screenshot modal |
| Repo | `repo_find` resuelve bbox | `repo_action` Highlight OK |

## Tabla de resumen (obligatoria al terminar flujo)

Al cerrar **cada** flujo NP-XX, pegar en chat:

```markdown
### Resumen NP-XX — <nombre>

| Paso | Tool | Resultado | Evidencia breve |
|------|------|-----------|------------------|
| 1 | list_windows | OK | 9 ventanas; sin modales notepad |
| 2 | ... | OK/FAIL | ... |

**Flujo:** met | partial | fail  
**Recovery usado:** ninguno | L1 cierre modal | L3 kill+relaunch  
**Actualizado:** state.json notepad_matrix NP-XX
```

## Tabla de avance objetivo (obligatoria al terminar turno)

```markdown
### Avance objetivo MCP

| Métrica | Valor | Meta |
|---------|-------|------|
| notepad_matrix met | X/30 | 30 |
| tool_validation fail | N | 0 |
| blockers activos | N | 0 |
| objective_met | false | true |
| Criterio Patterns por rol | partial/met | met |
| Criterio Eficiencia | fail/met | met |
```

## Evaluación de cierre (obligatoria al finalizar pruebas)

**Cuándo:** último flujo del lote, sesión NP completa, o al marcar `notepad_perfect` / `objective_met`.

**No alcanza** con esta tabla de avance sola. Además entregar la plantilla completa en:

[test-closure-evaluation.md](../../awdui-flow-exploration/patterns/test-closure-evaluation.md)

**Regla:** matriz 30/30 `met` **≠** MCP perfecto. Si hubo workarounds (coords, verify extra,
foco manual, atajos locale solo en skill), el veredicto de **calidad MCP (nivel 3)** debe ser
**NO** o **PARCIAL**, con tabla de fixes pendientes y flujos de regresión sugeridos.

## Orden de lectura antes de ejecutar

1. Este archivo (`protocol/agentic-execution.md`)
2. [recovery.md](recovery.md)
3. Flujo concreto `flows/NP-XX-*.md`
4. Modal si aplica `modals/*.md`
5. [element-map.md](../element-map.md) para IDs
6. `state.json` → `notepad_matrix`, `blockers`

## Anti-patrones documentados (2026-09-06)

- **Mezclar flujos:** NP-18 (watcher) dejó `Guardar como` abierto → NP-10 recibió teclado en picker `Abrir`.
- **Escape sin verify:** `send_keys escape` reportó OK pero modal seguía en `list_windows`.
- **Type sin foco:** `type_text` escribió en `Nombre de archivo` del diálogo, no en editor.
- **list_elements sin baseline:** árbol incluyó controles de modal stale → diagnóstico erróneo.
- **Parchear síntoma:** reintentar `ctrl+f` sin cerrar `Abrir` primero.

# Ventana activa — principio general (cualquier app de escritorio)

Las aplicaciones de escritorio (WinForms, WPF, Electron, Java Swing, etc.) procesan casi todo en la **ventana que tiene el foco del sistema operativo**. El target MCP (`set_target_window`) define *dónde buscar* controles; el foco define *dónde llegan* clic y teclado.

**`focus_policy=minimal` (default):** `list_elements`, `invoke_element`, `read_element`, etc. funcionan **sin** traer la app al frente. Solo se enfoca para pointer/teclado (`click`, `type_text`) cuando el target no está ya en primer plano. Si el operador dejó la app visible, reutilizarla sin `focus_window`.

Confundir ambos produce el error más común: actuar en la ventana equivocada, dejar modales abiertos, o creer que un paso terminó cuando solo cambió UIA en el fondo.

## Regla central

**Antes de cada acción (o al menos antes de cada paso del flujo): evaluar qué ventana está activa y qué se espera de ella.**

No es una regla de un producto ni de un botón Guardar. Es cómo funcionan las GUIs en general.

## Ciclo de evaluación

```
1. ¿Qué ventana tiene el foco ahora?
   → get_focused_element / list_windows (títulos visibles) / screenshot si hay duda

2. ¿Es la ventana donde debo trabajar en este momento?
   → Sí → actuar solo dentro de ella
   → No → decidir: completar la ventana activa primero, o cerrarla, o traer la correcta al frente

3. Después de la acción: ¿cambió la ventana activa?
   → Si abrí un diálogo/modal → estoy en un SUB-FLUJO; la ventana padre queda en espera

4. Antes de volver al flujo padre: ¿el diálogo terminó y cerró?
   → list_windows sin esa ventana, o foco de vuelta en el padre
```

## Sub-flujo modal (obligatorio)

Cuando una acción **abre** otra ventana (Buscar, Guardar como, Confirmar, picker, wizard):

| Fase | Qué hacer |
|------|-----------|
| **Entrada** | Anotar: "abrí `<título>` desde `<ventana padre>`". El target de trabajo pasa a ser el diálogo. |
| **Dentro** | Todas las tools scoped a `window_title` del diálogo. Completar la tarea *en esa ventana* (buscar, seleccionar, OK). |
| **Salida** | Verificar cierre: la ventana ya no está en `list_windows`, o el foco volvió al padre. |
| **Retorno** | Solo entonces continuar en el formulario principal. |

**Prohibido:** seguir llenando combos o clickear Guardar en el padre mientras el modal sigue abierto.

Un modal abierto no es "ruido": es el **estado actual de la aplicación**. Hay que resolverlo o cerrarlo explícitamente.

## Cuándo usar screenshot (modo aprendizaje / diagnóstico)

Screenshot **no** es para seguir clickeando a ciegas. Es para **entender** cuando:

- El foco no coincide con lo que UIA reporta
- Una acción "tuvo éxito" en JSON pero la pantalla no cambió
- Hay más de una ventana del mismo proceso (MDI, modales, tool windows)
- No sabés si debés actuar en el padre o en el hijo

Secuencia de diagnóstico:

```
1. screenshot_window (ventana que creés activa)
2. list_windows → ver si hay otra ventana encima
3. get_focused_element → qué control tiene foco real
4. Conclusión: ¿qué ventana hay que cerrar, completar o traer al frente?
```

Recién después de esa conclusión, elegir la siguiente acción programática.

## Relación con `set_target_window`

| Concepto | Rol |
|----------|-----|
| `set_target_window` | Alcance de búsqueda UIA y default de `window_title` |
| Ventana activa (OS) | Destino de mouse/teclado; define el sub-flujo actual |
| Ventana modal abierta | Sub-flujo con prioridad sobre el padre hasta cerrarse |

Si abrís un diálogo, podés mantener `set_target_window` en el padre **pero** las acciones inmediatas deben usar `window_title` del diálogo y el foco debe estar ahí.

## Señales de que violaste esta regla

- `list_windows` muestra una ventana que no debería existir (ej. "Buscar" después de un lookup)
- UIA del padre muestra valores "correctos" pero botones de acción siguen deshabilitados
- Clics o teclas no producen efecto visible
- Screenshot del padre se ve bien pero hay otra ventana encima en `list_windows`

En todos esos casos: **parar el flujo**, evaluar ventana activa, no reintentar el mismo click en el padre.

## Aplica a

- Diálogos modales WinForms (`ShowDialog`)
- File pickers nativos y de terceros
- MDI con forms hijos
- WPF `Window` modales
- Electron `dialog` / overlays que capturan foco
- Popups Java Swing
- Cualquier flujo donde "abrí algo" implique un paso intermedio obligatorio

## No confundir con

- Reglas de un producto (IDs, combos, Guardar) → skill del producto
- Estrategia de interacción de un control → `discover_control_interaction`
- Este patrón solo responde: **¿en qué ventana estoy y qué hago antes de seguir?**

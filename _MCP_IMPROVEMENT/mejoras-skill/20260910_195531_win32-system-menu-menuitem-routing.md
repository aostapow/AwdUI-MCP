# Win32 menú Sistema (title bar): routing MenuItem ExpandCollapse

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 19:55:31 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | `awdui-mcp-automejora/references/patterns/control-catalog.md` (fila MenuItem), `references/evaluacion-lab.md` |
| **Tipo de gap** | routing_tool |
| **Nivel** | L4 |
| **Impacto** | medio |
| **MCP versión** | v0.4.0 |

## Resumen

**Problema:** El catálogo indica `invoke_element` para MenuItem, pero el **menú Sistema** de ventana
Win32 (icono/título «Sistema») suele exponer solo **ExpandCollapse** para abrir el dropdown, no
Invoke ejecutable. F-11 lab encola «Invoke MenuItem Sistema»; el agente obedece → fail → workaround
`click_element`. Sin guía explícita, cada corrida repite el mismo par de intentos.

**Solución:** Bloque corto en **control-catalog** § MenuItem + nota en **evaluacion-lab** (seeds
Win32 shell):

1. **Abrir submenú** (flecha/chevron, menú sistema ventana): `click_element(role="MenuItem", …)` o
   `expand_element` — no asumir que `invoke_element` sin `role` resuelve el nodo correcto.
2. **Ejecutar acción** del ítem ya visible (Cerrar, Pegar): `invoke_element` / SelectionItem según
   patterns del ítem hoja.
3. Seeds lab: redactar success_criteria como «desplegar menú Sistema» sin mandar Invoke como única
   vía ACT.

**Dónde:** `control-catalog.md` fila MenuItem; `evaluacion-lab.md` § Win32 Explorer/title chrome.

## Texto propuesto

### MenuItem — menú sistema de ventana (Win32)

Controles tipo **Sistema** en la barra de título (`MenuItem`, patterns **ExpandCollapse**, sin
Invoke fiable):

| Intención | Tool | Notas |
|-----------|------|-------|
| Abrir dropdown | `click_element(name=…, role="MenuItem")` o `expand_element` | Pasar **`role`**; evitar `invoke_element` solo por name |
| Elegir ítem hoja | `invoke_element` o `click_element` según `discover_control_interaction` | Tras `list_elements(role=MenuItem)` en popup |
| Cerrar sin acción | `press_key` Escape ×1–2 | Tras verificar hijos Restaurar/Mover/Cerrar |

## Contexto del turno

F-11 met con WARN; invoke fail / click ExpandCollapse OK; lab 10/50.

## Test de abstracción

Cualquier app Win32 con menú sistema estándar (Explorador, Notepad, consolas) — no AST ni producto
concreto.

## Verificación duplicados

| Archivo | Relación |
|---------|----------|
| `mejoras-skill/20260905_123600_control-catalog-expand-element-routing.md` | **Fusionar** al implementar: una sola pasada control-catalog |
| `aceptadas/.../20260906_171701_win32-menubar-cascade-escape.md` | Complementario — Escape tras cascada menubar, no menú Sistema |

## Criterio de aceptación

- [ ] Texto sin rutas lab ni AST.
- [ ] `flows.json` plantilla lab recomienda ACT expand, no solo Invoke.
- [ ] Tras fix código `invoke_element`+role, doc sigue recomendando role en ambas tools.

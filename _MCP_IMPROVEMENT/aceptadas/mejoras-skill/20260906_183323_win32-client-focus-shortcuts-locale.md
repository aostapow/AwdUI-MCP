# Win32: foco en cliente + atajos locale (no asumir Ctrl+A)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | aplicada |
| **Fecha** | 2026-09-06 18:33:23 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | awdui-flow-exploration/patterns/win32-menubar.md |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **MCP versión** | v0.4.0 |

## Resumen

**Problema:** (1) Tras `focus_window` con `focus_policy=minimal`, el foco de teclado no cae en
el `Document`/`Edit` del cliente; operaciones de menú contextual, selección y atajos fallan o
abren modales inesperados hasta hacer clic explícito en el editor. (2) `win32-menubar.md` lista
«Seleccionar todo | Ctrl+A» como atajo genérico; en Notepad Win11 ES **Ctrl+A = Abrir** (modal)
y **Seleccionar todo = Ctrl+E** — el agente bloqueó NP-24 hasta descubrir el mapa de producto.

**Solución:** En el patrón genérico Win32: (a) paso obligatorio «foco cliente» antes de teclado/
menú contextual — `click_element` en área Document/Edit o `get_focused_element` verify; (b) tabla
de atajos genéricos sin afirmar Ctrl+A universal; (c) regla «consultar skill de producto para
atajos locale (Win11 ES) antes de `send_keys`».

**Dónde:** `patterns/win32-menubar.md` (secciones Recuperación + Atajos); enlace desde
`patterns/active-window.md`; skill `notepad/element-map.md` ya correcto — referenciar desde genérico.

## Contexto del turno

- NP-24: `Ctrl+A` abrió diálogo Abrir/guardar; root cause Archivo id=2 vs Seleccionar todo id=25
  (`Ctrl+E`). Flujo completado con atajo correcto + clipboard + screenshots.
- NP-25: `focus_window` solo no bastó; requirió clic en editor para foco Edit antes de menú
  contextual y cadena cortar/pegar.
- Skills leídas: `awdui-mcp-objective`, `notepad` (mapa atajos ya en `element-map.md` y NP-24).

## Texto propuesto

### Foco en área cliente (antes de teclado y menú contextual)

`focus_window` con `focus_policy=minimal` **no garantiza** foco de entrada en el control
`Document`/`Edit` del cliente.

| Paso | Acción | Verify |
|------|--------|--------|
| 1 | `focus_window` ventana objetivo | ventana foreground |
| 2 | `click_element` en Document/Edit **o** centro del rect cliente | `get_focused_element` → role Document/Edit |
| 3 | Teclado / clic derecho / menú contextual | sin modal espurio en `list_windows` |

**Anti-patrón:** `send_keys` o `right_click_element` inmediatamente tras `focus_window` sin verify
de foco en editor.

### Atajos de teclado — no asumir US/default

La tabla genérica puede listar atajos **habituales**, pero builds localizados (ej. Win11 ES) pueden
reasignar combinaciones (Notepad: Ctrl+A → Abrir, Ctrl+E → Seleccionar todo, Ctrl+B → Buscar).

| Regla | Acción |
|-------|--------|
| Antes de atajo en app con skill de producto | Leer `element-map.md` / submenú MenuItem con accelerator en name |
| Sin skill de producto | `list_elements(MenuItem)` tras abrir menú **o** `spy_inspect` accelerator |
| Tras modal inesperado | Recovery L1: Cancelar + verificar `list_windows` antes de reintentar |

**Cambio en tabla genérica:** reemplazar fila «Seleccionar todo | Ctrl+A» por «Seleccionar todo |
*ver skill producto / menú Edición* (ej. Ctrl+E Win11 ES Notepad)».

## Verificación de duplicados

- **Extiende** `20260906_171701_win32-menubar-cascade-escape.md` (aplicada) — recovery menciona
  clic editor pero no como paso obligatorio pre-teclado ni atajos locale.
- **No duplica** `notepad/flows/NP-24` — producto ya documenta Ctrl+E; esta propuesta evita que
  el patrón **genérico** contradiga al producto.

## Test de abstracción (L3)

Aplica a cualquier app Win32 con editor cliente + menú (Notepad, WordPad legacy, editores simples).
No lista automation_ids de un producto en las reglas centrales.

## Esfuerzo observado

- NP-24: un ciclo bloqueado por modal Abrir tras Ctrl+A incorrecto.
- NP-25: reintento tras detectar foco insuficiente sin clic en editor.

## Criterio de aceptación

- [ ] `win32-menubar.md` sin «Ctrl+A = Seleccionar todo» como hecho universal.
- [ ] Sección «Foco cliente» con verify `get_focused_element` antes de menú contextual.
- [ ] Enlace desde `awdui-flow-exploration/SKILL.md` Fase 0 o Fase 3.
- [ ] Skill `notepad/SKILL.md` quirks referencia el patrón genérico (sin duplicar texto largo).

## Beneficios futuros

- Menos modales espurios por atajos locale incorrectos en harness Win32.
- NP-25+ y flujos con menú contextual más estables sin depender de coords manuales por foco roto.

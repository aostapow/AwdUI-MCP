# Patrón Win32: menú cascada — cerrar antes del siguiente top-level

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | aplicada |
| **Fecha** | 2026-09-06 17:17:01 |
| **Skill objetivo** | awdui-flow-exploration/patterns/win32-menubar.md (nuevo) |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Impacto** | medio |
| **MCP versión** | v0.4.0 |

## Resumen

**Problema:** En Notepad Win32, tras `invoke_element(Archivo)` exitoso, `click_element` /
`invoke_element` en **Edición** falló porque el submenú Archivo seguía abierto. Win32 menu bars
solo exponen hijos `MenuItem` del menú **activo**; un segundo top-level con otro menú abierto
devuelve not found o hit en coordenadas incorrectas.

**Solución:** Documentar patrón cross-app en skill genérica (no solo `notepad/`):

1. Tras operar en un submenú, **cerrar** antes de otro top-level: `Escape`, clic en área cliente
   (editor), o `Alt` para desplegar otro menú limpio.
2. Preferir **atajos** (`send_keys`) cuando el menú es frágil: Ctrl+S, Ctrl+F, Alt+F4.
3. Secuencia: `invoke` menú → `list_elements(role=MenuItem)` hijos → acción → **cerrar** → siguiente menú.
4. Verificar con `get_focused_element` que el foco no quedó en `MenuItem` huérfano.

**Dónde:** Nuevo `patterns/win32-menubar.md`; enlace desde Fase 3 de `awdui-flow-exploration`
y desde `patterns/control-catalog.md` (rol `MenuItem`).

## Contexto del turno

- Notepad harness: `invoke_element(Archivo)` 295 ms OK; items Guardar como visibles.
- `click_element(Edición)` FAIL inmediatamente después — menú Archivo aún desplegado.
- Skill producto `notepad/SKILL.md` ya documenta quirk #2; falta patrón **genérico Win32**
  reutilizable (Bloc de notas, Paint, apps Win32 legacy).

## Texto propuesto

### Menú bar Win32 (MenuItem cascada)

Win32 expone `MenuItem` top-level (Archivo, Edición, …). Solo un submenú visible a la vez.

| Paso | Acción |
|------|--------|
| Abrir menú | `invoke_element(name="Archivo", role="MenuItem")` |
| Listar hijos | `list_elements(role="MenuItem", max_depth=4)` — hijos del submenú abierto |
| Elegir ítem | `invoke_element` o `click_element` en hijo con `automation_id` estable |
| **Cerrar** | `send_keys("{ESC}")` o clic en cliente (Document/Edit) antes de otro top-level |
| Siguiente menú | Repetir invoke en otro top-level **solo** si submenú anterior cerró |

**Atajos preferidos** cuando invoke es frágil: documentar en skill de producto; genérico:
`Ctrl+combinación` vía `send_keys` / `press_key_combo`.

**Anti-patrón:** encadenar `invoke_element(Archivo)` → `invoke_element(Edición)` sin cerrar.

## Verificación de duplicados

- Skill `notepad/SKILL.md` quirk #2 cubre el mismo síntoma **en Notepad** — esta propuesta
  **generaliza** a L3 sin IDs de producto.
- No duplica `active-window.md` (sub-flujo modal) — menús no son modales `#32770`.
- No propone cambio MCP; `invoke_element` comportamiento correcto.

## Test de abstracción

Aplica a cualquier app Win32 con menu bar UIA (`notepad.exe`, `mspaint.exe`, utilidades legacy).
No depende de automation_ids de Notepad.

## Criterio de aceptación

- [ ] Archivo `patterns/win32-menubar.md` sin nombres ES específicos de Notepad en reglas centrales.
- [ ] Enlace desde `awdui-flow-exploration/SKILL.md` Fase 3 (rol MenuItem).
- [ ] Skill `notepad/` referencia el patrón genérico en lugar de duplicar texto largo.

## Beneficios futuros

- Menos reintentos `click_element` post-menú en harness Win32.
- Agentes nuevos en productos Win32 sin skill dedicada siguen secuencia segura.

## Esfuerzo observado

- Un fallo explícito `click_element Edición` post-menú Archivo; recuperación manual con Escape
  o atajos no documentada en skill genérica hasta creación de `notepad/`.

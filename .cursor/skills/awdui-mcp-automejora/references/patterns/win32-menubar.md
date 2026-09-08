# Patrón Win32 — menú bar cascada (MenuItem)

Aplica a apps **Win32 clásicas** con barra de menú UIA (`notepad.exe`, `mspaint.exe`, utilidades legacy).
Catálogo general: [control-catalog.md](control-catalog.md) · ventana activa: [active-window.md](active-window.md).

## Regla central

Win32 expone `MenuItem` top-level (Archivo, Edición, Formato, …). **Solo un submenú visible a la vez.**
Abrir un segundo top-level mientras el primero sigue desplegado → `invoke_element` / `click_element` fallan o resuelven mal.

## Secuencia segura

| Paso | Acción | Tool |
|------|--------|------|
| 1 | Abrir menú | `invoke_element(name=<top>, role="MenuItem")` |
| 2 | Listar hijos | `list_elements(role="MenuItem", max_depth=4)` |
| 3 | Elegir ítem hijo | `invoke_element` / `click_element` en hijo |
| 4 | **Cerrar submenú** | `send_keys("escape")` **o** foco en cliente (Document/Edit) |
| 5 | Verificar foco | `get_focused_element` — role Document/Edit, no MenuItem huérfano |
| 6 | Siguiente top-level | Repetir paso 1 solo si paso 4 OK |

## Atajos preferidos (cuando menú es frágil)

Preferir `send_keys` / `press_key_combo` sobre cascada de menús:

| Intención | Atajo típico |
|-----------|--------------|
| Guardar | Ctrl+S |
| Guardar como | Ctrl+Mayús+S |
| Buscar | Ctrl+F |
| Reemplazar | Ctrl+H |
| Ir a línea | Ctrl+G |
| Salir | Alt+F4 |
| Seleccionar todo | *ver skill producto / menú Edición* (ej. Ctrl+E Win11 ES Notepad; **no** asumir Ctrl+A) |

Documentar atajos específicos en skill de **producto**; builds localizados pueden reasignar combinaciones.

## Foco en área cliente (antes de teclado)

`focus_window` con `focus_policy=minimal` **no garantiza** foco de entrada en `Document`/`Edit`.

| Paso | Acción | Verify |
|------|--------|--------|
| 1 | Target + `focus_window` si hace falta | ventana foreground |
| 2 | Teclado / menú contextual | MCP auto: `ensure_client_focus` antes de `send_keys`/`type_text` cuando hay target Win32 |
| 3 | Si falla atajo o abre modal espurio | `get_focused_element` → Document/Edit; consultar skill producto para atajo locale |

**Anti-patrón:** `send_keys` o `right_click_element` inmediatamente tras `focus_window` sin verify de foco en editor.

## Anti-patrones

- Encadenar `invoke_element(MenúA)` → `invoke_element(MenúB)` **sin cerrar** submenú A
- `click_element` en top-level B con submenú A aún abierto
- Asumir que `list_elements(role=MenuItem)` lista todos los menús — solo hijos del **activo**
- Reintentar el mismo invoke en B sin Escape (loop infinito)

## Recuperación tras fallo

```
send_keys("escape")           → cerrar submenú
click_element / focus editor  → devolver foco al cliente
get_focused_element           → confirmar Document/Edit
```

Si persiste: `focus_window` + atajo de teclado en lugar de menú.

## Relación con modales

Los menús **no** son modales `#32770`. Para diálogos (Guardar como, Buscar) ver [active-window.md](active-window.md) y cambiar `set_target_window` al título del diálogo.

## Skills de producto

Quirks locales (títulos ES, automation_ids) van en `.cursor/skills/{producto}/` — este archivo es **genérico Win32**.

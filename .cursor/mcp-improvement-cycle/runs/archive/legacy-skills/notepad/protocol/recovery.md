# Playbook de recuperación — Notepad harness

Ejecutar **en orden** cuando un paso falla o el estado UI no coincide con el esperado.
Narrar en chat: "Recovery L1 — …" antes de cada acción.

## Cuándo activar recovery

- `list_windows` muestra ventana no esperada (`Abrir`, `Guardar como`, `Fuente`, `Bloc de notas` confirm-save)
- `get_focused_element` apunta a control de otro diálogo (ej. `SearchEditBox` del picker)
- `read_element` / `set_element_value` en id=15 falla con COM error
- Teclado no produce efecto en editor tras `send_keys`
- Texto del editor corrupto / mezclado con intentos fallidos
- Más de un modal `#32770` de `notepad.exe` apilado

## L0 — Diagnóstico (siempre primero)

```
1. list_windows          → inventariar ventanas notepad.exe + modales #32770
2. get_focused_element   → dónde está el foco real
3. screenshot scope=window window_title="Bloc de notas"  (solo si duda)
```

Anotar en chat qué ventana sobra y cuál falta.

## L1 — Cerrar modales stale (preferido)

Por cada modal `#32770` **no deseado**, en orden de arriba hacia abajo:

```
1. focus_window("<título modal>")
2. invoke_element(name="Cancelar", window_title="<título>")   # id=2 usual
   — o — send_keys("escape")
3. list_windows  → VERIFY: título modal AUSENTE
```

| Modal | Título UIA | Cancelar |
|-------|------------|----------|
| Abrir | `Abrir` | Cancelar id=2 |
| Guardar como | `Guardar como` | Cancelar id=2 |
| Fuente | `Fuente` | Cancelar id=2 |
| Confirmar | `Bloc de notas` | "No guardar" / id según [confirm-save.md](../modals/confirm-save.md) |
| Buscar clásico | `Buscar` | Cancelar |

**Regla:** repetir L1 hasta `list_windows` sin modales notepad **o** hasta 3 intentos por modal.
Si tras 3 intentos sigue visible → L3.

## L2 — Restablecer foco en Notepad (sin matar proceso)

```
1. focus_window("Bloc de notas")
2. set_target_window("Bloc de notas", focus_policy="minimal")
3. send_keys("escape")                    # cerrar menús cascada abiertos
4. get_focused_element  → VERIFY: Edit/Document id=15 o MenuBar
5. read_element(automation_id="15")       → VERIFY: value legible
```

Si editor ilegible → `ctrl+z` repetido o L3.

## L3 — Kill proceso y relanzar (último recurso)

Cuando L1+L2 no dejan baseline limpio:

```
1. close_app(process="notepad.exe")   — o — close_app(title="Bloc de notas")
2. list_windows  → VERIFY: sin notepad.exe
3. launch_app("notepad.exe", reuse=false)
4. set_target_window("Bloc de notas")
5. focus_window("Bloc de notas")
6. list_windows  → VERIFY: una ventana Notepad, sin modales
```

**Nota:** `reuse=false` o `replace=true` según tool; invalidar expectativas de archivo previo (`Sin título`).

## L4 — Recovery post-kill por flujo

| Flujo interrumpido | Re-preparación mínima |
|--------------------|------------------------|
| NP-02..NP-03 | Escribir texto seed documentado en flujo |
| NP-04..NP-05 | Crear/abrir archivo según flujo |
| NP-10..NP-11 | Pegar texto multi-línea seed (ver NP-10 paso 3) |
| NP-18 | Documento con cambios sin guardar (`*título`) |

## Baseline limpio (definición)

Antes de **iniciar** cualquier flujo NP-XX:

| Check | Esperado |
|-------|----------|
| `list_windows` | 1× `Notepad/notepad.exe` principal; 0× `#32770` |
| `get_target_window` | `Bloc de notas` |
| `get_focused_element` | control de ventana Notepad (no picker) |

Si no se cumple → L1 o L3 **antes** del paso 1 del flujo.

## Qué NO hacer en recovery

- No enviar `ctrl+f` / `ctrl+h` / `alt+f4` con modales abiertos
- No usar `list_elements` profundo mientras hay picker (contamina árbol)
- No asumir que `invoke_element Cancelar` cerró sin `list_windows`
- No continuar otro flujo NP distinto sin baseline limpio

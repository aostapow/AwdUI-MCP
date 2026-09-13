# Post-invoke: ventana ajena (navegador) — cierre sin destruir target

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 20:05:30 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | awdui-mcp-automejora/references/patterns/active-window.md |
| **Tipo de gap** | routing_tool |
| **Nivel** | L4 |
| **Versión MCP** | v0.4.0 |

## Resumen

**Problema:** Tras `invoke_element` en acciones tipo «Ayuda», muchas apps Win32 abren **Edge/Chrome**
(proceso ajeno) en lugar de un panel in-app. El agente buscó controles de ayuda en el Explorador
(`find_element` ~13 s NOT FOUND) y cerró con **Alt+F4** sin verificar foreground → cerró la ventana
**lab** (`set_target_window` fail) y el recovery con `launch_app` eliminó **5** instancias duplicadas.

**Solución:** Patrón genérico post-invoke: (1) `list_windows` inmediato y clasificar «nueva ventana
browser» vs panel mismo PID; (2) si browser → `focus_window` en esa ventana y **Ctrl+W** (o Alt+F4
**solo** con verify foreground = browser); (3) **nunca** Alt+F4 con target lab aún registrado sin
confirmar que foreground ≠ target; (4) recovery: `launch_app` con ruta/carpeta lab y `replace=true`
controlado, no barrido que cierre duplicados masivos.

**Dónde:** Nuevo `patterns/foreign-process-dismiss.md` + enlace desde `active-window.md` y
`evaluacion-lab.md` § recovery; referencia en `docs/AGENT_GUIDE.md`.

## Contexto del turno

- Lab `escritorio-windows-2026-09-10`, flujo **F-15** «Abrir panel Ayuda».
- `invoke_element` botón Ayuda ~1188 ms OK → ayuda en **Edge**, no panel UIA en Explorador.
- `find_element` negativo ~13383 ms SLOW; `press_key_combo` Alt+F4; `set_target_window` fail;
  `launch_app` partial «closed 5 duplicates»; recovery manual + probe 402 ms OK.
- `improvements.jsonl` ítem **#8** (`press_key_combo` / Ayuda / Alt+F4 side-effect).

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| Alt+F4 cerró Explorador lab | routing_tool | L4 | Sí (este archivo) |
| find 13s panel in-app inexistente | routing_tool | L3 | Sí — paso list_windows antes de find |
| launch_app 5 duplicados | entorno | L3 | Sí — subsección recovery lab |
| Ayuda abre Edge (producto) | sintoma_app | L1 | No hardcodear «Ayuda» — patrón browser genérico |

Parcialmente cubierto por skill **aplicada** `win32-client-focus-shortcuts-locale` (foco antes de
teclado), pero **no** documenta navegador ajeno post-invoke ni anti-patrón Alt+F4 vs target.

## Texto propuesto

### Clasificar resultado tras invoke (antes de find profundo)

1. `list_windows` (filtrar por título/proceso: `msedge`, `chrome`, `firefox` o ventana nueva no-PID-target).
2. Si aparece browser con título coherente con la acción → **no** buscar panel in-app con `find_element`
   largo; marcar éxito VERIFY como «ayuda externa visible» (screenshot opcional).
3. Si no hay ventana nueva → continuar UIA en target (`list_elements` acotado).

### Cerrar ventana ajena sin tocar target

| Paso | Acción | Verify |
|------|--------|--------|
| 1 | `focus_window` título/proceso del browser | foreground = browser PID |
| 2 | `press_key_combo` **Ctrl+W** (pestaña) o Alt+F4 **solo** si paso 1 OK | browser ausente en `list_windows` |
| 3 | `set_target_window` / `focus_window` ventana lab | `check_session_status` target vivo |
| 4 | Probe ligero (`find_element` id conocido o `get_focused_element`) | &lt; 3 s |

**Anti-patrón:** `press_key_combo` Alt+F4 inmediatamente tras invoke sin `list_windows` + focus en
ventana a cerrar.

### Recovery si el target murió por error de agente

1. Anotar ruta/carpeta lab del flujo (`window_context` en `flows.json`).
2. `launch_app` con path explícito a `explorer.exe` + argumento carpeta, **`replace=true`** solo si
   hay instancias huérfanas documentadas — evitar cierre masivo de ventanas del usuario.
3. `set_target_window` por título normalizado; re-probe antes de marcar `met`.

## Test de abstracción (L4)

Aplica a cualquier Win32/UWP que delegue ayuda/documentación a navegador (Explorador, Office, apps
con F1→browser) sin nombrar automation_id de un producto.

## Verificación de duplicados

| Propuesta existente | Relación |
|---------------------|----------|
| `20260906_183323` win32-client-focus (aplicada) | Complementar — no cubre browser ajeno |
| `20260907_232300` flyout dismiss hygiene | Distinto — flyouts mismo PID |
| `20260910_195126` find negative wall-clock | Complementario — evitar find inútil post-invoke |

## Criterio de aceptación

- [ ] Texto sin «Explorador Ayuda» como regla única; ejemplos como ilustración
- [ ] Enlace desde `evaluacion-lab.md` recovery y `awdui-gui-safety` (no Alt+F4 ciego)
- [ ] F-15 lab: re-ejecutar con Ctrl+W tras focus Edge sin perder ventana lab

## Beneficios futuros

- Menos cierres accidentales de ventana objetivo en lab y producto.
- Menos `launch_app` agresivo y duplicados en recovery.
- Encadena con fast-fail find (`195126`) al omitir búsqueda in-app cuando browser ya visible.

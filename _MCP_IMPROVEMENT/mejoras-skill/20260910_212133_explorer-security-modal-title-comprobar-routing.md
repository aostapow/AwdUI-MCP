# Explorer — modal seguridad: título archivo/carpeta, Comprobar sin find lento, no Ayuda

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 21:21:33 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | `awdui-mcp-automejora/references/evaluacion-lab.md` § Explorer NTFS / seguridad |
| **Tipo de gap** | routing_tool, deteccion |
| **Nivel** | L3 |
| **Versión MCP** | v0.4.0 (check_version: up to date) |

## Resumen

**Problema:** En flujos lab F-22/F-76 (modal «Configuración avanzada de seguridad» / pestaña
«Acceso efectivo»), el agente fija `set_target_window` con el título de **carpeta** del lab
mientras el diálogo `#32770` muestra título distinto si el objeto es **archivo** vs **carpeta**
→ scope equivocado, `find_element`/`find_text` sobre «Comprobar» ~17 s y riesgo de actuar en el
árbol del Explorador. Recovery con `launch_app` cerró ventanas lab (ver backlog `200530`).
Desvío a cinta **Ayuda** (Edge) rompe la ruta Seguridad → modal. `repo_hints_set` falló por repo
vacío (backlog `200820` — no duplicar tool).

**Solución:** Playbook L3 cross-app Win32: (1) tras abrir seguridad avanzada, resolver modal solo
con `list_windows` / owned `#32770` del PID Explorer — **no** asumir título de carpeta lab;
(2) `set_target_window(window_handle=…)` o subcadena estable (`Configuración avanzada`, `seguridad`);
(3) pestañas: `invoke_element` `TabItem` «Acceso efectivo» (patrón ya ~512 ms OK en F-76);
(4) «Comprobar»: `list_elements(role=Button, max_depth=4)` **en scope modal** o `invoke_element`
con `window_handle` — **prohibido** `find_element(name=Comprobar)` sin HWND del modal;
(5) ruta F-22/F-76: **no** `invoke` Ayuda en cinta; (6) hints: `repo_capture` del botón/tab
antes de `repo_hints_set`.

**Dónde:** Nueva subsección «Explorer — modal NTFS (owned #32770)» en `evaluacion-lab.md`;
cross-ref `patterns/active-window.md`, código pendiente `20260910_201130` (owned_modal auto).

## Contexto del turno

- **Turno:** execute **F-76** Acceso efectivo (parent F-22), lab Escritorio Windows 2026-09-10.
- **OK:** `invoke` TabItem «Acceso efectivo» **512 ms**; verify panel efectivo + Cancel ~220 ms.
- **Fricción:** Explorer desvío **Ayuda**; `launch_app` recovery cerró instancias lab;
  `find` «Comprobar» **~17 s** SLOW; título modal **archivo vs carpeta** vs target carpeta;
  `repo_hints_set` → repo vacío (`object not found`).

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| Título modal ≠ título carpeta lab | deteccion | L3 | Sí (este archivo) |
| find Comprobar 17 s sin scope modal | routing_tool | L3 | Sí (este archivo) |
| Desvío Ayuda en ruta seguridad | routing_tool | L3 | Sí (este archivo) |
| launch_app cerró lab | entorno | L3 | No — `20260910_200530` |
| repo_hints_set sin objeto | tool_gap | L4 | No — `20260910_200820` |
| Tab Acceso efectivo 512 ms | — | — | No — ejecución OK |

## Texto propuesto

### Explorer — modal NTFS (owned `#32770`)

**Precondición:** Explorador con carpeta/archivo lab; modal abierto desde Propiedades → Seguridad
→ Seguridad avanzada (mismo PID que Explorer).

1. **OBS:** `list_windows` filtrar `class=#32770` owned del PID target; guardar `hwnd` + `title`
   (el título **incluye el nombre del objeto** — archivo o carpeta — no el path del lab).
2. **Target:** `set_target_window(window_handle=<hwnd_modal>)` o título parcial
   `Configuración avanzada` / `seguridad` — **no** reutilizar solo el título de la ventana
   Explorador de carpeta si el modal ya está abierto.
3. **Pestañas:** `find_element(role=TabItem, name=Acceso efectivo)` o `invoke_element` con
   `window_handle` del modal; evitar `find` global con Explorer+modal en scope padre (ver
   `20260910_201130`).
4. **Comprobar / Aplicar:** `list_elements(role=Button, max_depth=4)` en scope modal →
   `invoke_element` por `name` o `automation_id`; si miss <2 s, `focus_window(modal)` y reintento
   — **no** barrido `find_element` sin `window_handle` (evitar ~17 s).
5. **Anti-ruta:** En cola F-22/F-76/F-77 **no** invocar **Ayuda** en cinta (abre Edge); Seguridad
   vía contexto Propiedades / Seguridad avanzada ya mapeado.
6. **Repo:** Tras workaround o ID estable → `repo_capture` bajo
   `Escritorio/Explorer/ModalSeguridad/...` → luego `repo_hints_set` (o `ensure_minimal` cuando
   exista `200820`).

## test_abstraccion

Aplica a cualquier diálogo Win32 `#32770` owned (Notepad Buscar, permisos NTFS, pickers) donde el
título del modal refleja el objeto y no la ventana padre.

## verificacion_duplicados

| Archivo | Relación |
|---------|----------|
| `20260910_201130_owned-modal-auto-scope-without-foreground.md` | Código — reduce need de focus manual; skill complementa HWND/título |
| `20260910_200820_repo-hints-set-missing-path-actionable-error.md` | Tool — repo vacío |
| `20260910_200530_foreign-browser-dismiss-post-invoke.md` | Recovery launch_app / Ayuda |
| `20260910_195126_find-element-name-search-negative-wall-clock.md` | Código — techo miss find; skill evita find en árbol padre |

## esfuerzo_observado

F-76 met con Tab 512 ms; ~17 s en find Comprobar; recovery launch_app; Ayuda desvío; hints_set fail.

## beneficios_futuros

F-77 Permisos y subárbol F-163..175 sin SLOW find ni scope carpeta incorrecto; menos relaunch Explorer.

## Criterios de aceptación (mantenedor)

- [ ] Subsección en `evaluacion-lab.md` sin paths lab hardcodeados salvo nombres genéricos NTFS.
- [ ] Cross-ref `active-window.md` y backlog `201130`.
- [ ] Replay F-76: Comprobar/find <3 s o invoke directo; sin Ayuda; repo_capture antes de hints.

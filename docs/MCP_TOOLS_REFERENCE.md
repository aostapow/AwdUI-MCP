# AwdUI MCP — Catálogo de Tools

Referencia canónica para agentes de IA. Describe **cada tool** del servidor `awdui`, cuándo usarla y cómo.

- **Estrategia general:** [AGENT_GUIDE.md](AGENT_GUIDE.md)
- **Patrones por tipo de control:** [.cursor/skills/awdui-flow-exploration/patterns/control-catalog.md](../.cursor/skills/awdui-flow-exploration/patterns/control-catalog.md)
- **Última revisión:** 2026-09-06 (87 tools — `ascii_ui_view` ojo ASCII)
- **Mantener actualizado:** ver [.cursor/rules/awdui-tools-catalog.mdc](../.cursor/rules/awdui-tools-catalog.mdc)

---

## Índice rápido

| Sesión / foco | Tools |
|---------------|-------|
| **Target** | `set_target_window`, `get_target_window` |
| **Ventanas** | `list_windows`, `focus_window`, `launch_app`, `restore_window`, `virtual_desktop` |
| **Exploración UIA** | `find_element`, `find_all_elements`, `list_elements`, `get_snapshot`, `ascii_ui_view`, `read_element`, `read_element_by_index`, `get_focused_element`, `element_at_point`, `get_element_properties`, `discover_control_interaction`, `spy_inspect`, `spy_tree`, `ui_fingerprint`, `detection_health`, `detect_framework`, `check_java_bridge` |
| **Espera / verify UIA** | `wait_for_element`, `wait_for_condition`, `wait_for_input_idle`, `element_exists` |
| **Sesión / caché** | `check_session_status`, `invalidate_cache`, `release_all` |
| **Formularios** | `fill_form`, `get_all_values`, `set_element_value` |
| **Eventos UIA** | `start_event_monitor`, `stop_event_monitor`, `get_event_log` |
| **Acción UIA** | `click_element`, `invoke_element`, `expand_element`, `set_element_value`, `list_control_items`, `select_control_item`, `get_grid_item`, `read_table`, `scroll_into_view`, `realize_virtualized_item`, `find_item_by_property`, `scroll_element` |
| **Input coordenadas** | `click`, `type_text`, `send_keys`, `scroll`, `drag`, `hover`, `get_mouse_position` |
| **OCR / visual** | `find_text`, `click_text`, `smart_find`, `detect_visual_regions`, `find_by_template_tool` |
| **Screenshots** | `screenshot`, `wait_for_change`, `get_screen_size`, `screenshot_baseline`, `screenshot_diff` |
| **Repositorio QTP** | `repo_find`, `repo_list`, `repo_hints`, `repo_action`, `repo_capture` |
| **Descubrimiento** | `observe_ui_tool`, `plan_probes_tool`, `apply_probe_tool`, `discover_target_tool`, `spy_walk_visible_tool`, `build_detection_context` |
| **Batch / utilidades** | `batch_actions`, `clipboard`, `manage_screenshots`, `highlight_element`, `clear_highlight` |
| **Watcher** | `start_watcher`, `stop_watcher`, `get_notifications` |
| **Sistema** | `configure_uac`, `check_version`, `get_server_info` |

**Lista alfabética (87):**  
`apply_probe_tool`, `ascii_ui_view`, `batch_actions`, `build_detection_context`, `check_java_bridge`, `check_session_status`, `check_version`, `clear_highlight`, `click`, `click_element`, `click_text`, `clipboard`, `configure_uac`, `detect_framework`, `detect_visual_regions`, `detection_health`, `discover_control_interaction`, `discover_target_tool`, `drag`, `element_at_point`, `element_exists`, `expand_element`, `fill_form`, `find_all_elements`, `find_by_template_tool`, `find_element`, `find_item_by_property`, `find_text`, `focus_window`, `get_all_values`, `get_element_properties`, `get_event_log`, `get_focused_element`, `get_grid_item`, `get_mouse_position`, `get_notifications`, `get_screen_size`, `get_server_info`, `get_snapshot`, `get_target_window`, `highlight_element`, `hover`, `invalidate_cache`, `invoke_element`, `launch_app`, `list_control_items`, `list_elements`, `list_windows`, `manage_screenshots`, `observe_ui_tool`, `plan_probes_tool`, `read_element`, `read_element_by_index`, `read_table`, `realize_virtualized_item`, `release_all`, `repo_action`, `repo_capture`, `repo_find`, `repo_hints`, `repo_list`, `restore_window`, `screenshot`, `screenshot_baseline`, `screenshot_diff`, `scroll`, `scroll_element`, `scroll_into_view`, `select_control_item`, `send_keys`, `set_element_value`, `set_target_window`, `smart_find`, `spy_inspect`, `spy_tree`, `spy_walk_visible_tool`, `start_event_monitor`, `start_watcher`, `stop_event_monitor`, `stop_watcher`, `type_text`, `ui_fingerprint`, `virtual_desktop`, `wait_for_change`, `wait_for_condition`, `wait_for_element`, `wait_for_input_idle`

## Convenciones comunes

| Parámetro | Uso |
|-----------|-----|
| `window_title` / `title` | Título parcial de ventana. Si vacío → foreground o `set_target_window`. |
| `window_handle` | HWND de ventana modal/hija; alternativa a `window_title` en find/click/list/set/read/snapshot. |
| `automation_id` | ID WPF/WinForms (preferido sobre `name`). |
| `capture` | Screenshot post-acción. Default `false` (rápido). |
| `role` | Tipo UIA: `Button`, `Edit`, `ComboBox`, `Table`, etc. |

**Orden de preferencia al interactuar:** UIA (`find_element` → `invoke_element` / patterns) → repositorio → OCR (`find_text`) → coordenadas.

---

## 1. Sesión y ventana objetivo

### `set_target_window`

**Qué hace:** Fija la ventana objetivo de la sesión (scope UIA/input). `focus_policy` controla si se roba el foco del escritorio.
**Cuándo usarla:** Al iniciar automatización de una app (`set_target_window("AST")`).
**Parámetros clave:** `title` / `window_title` (parcial). Cadena vacía = limpiar target. `focus_policy`: **minimal** (default) | always | never — minimal observa/actúa por UIA sin foreground; solo enfoca para pointer/teclado si el target no está ya al frente.
**Evitar:** Dejar el target activo al terminar — `set_target_window("")` devuelve foco al terminal.
**Ejemplo:** `set_target_window("Calculadora", focus_policy="minimal")`
**Relacionadas:** `get_target_window`, `focus_window`, `check_session_status`
**Scope:** Con target activo, bloquea clics y acciones UIA fuera del proceso de la app objetivo.

### `get_target_window`

**Qué hace:** Devuelve el título parcial del target de sesión actual o indica que no hay target.
**Cuándo usarla:** Verificar scope antes de tools que no reciben `window_title` explícito.
**Parámetros clave:** — (sin parámetros).
**Evitar:** Asumir target sin consultar tras `release_all` o `set_target_window("")`.
**Ejemplo:** `get_target_window()`
**Relacionadas:** `set_target_window`, `check_session_status`

---

## 2. Ventanas y escritorio

### `list_windows`

**Qué hace:** Lista ventanas visibles con título, posición, tamaño (outer/client), DPI y proceso.
**Cuándo usarla:** Descubrir título exacto para `set_target_window`, `focus_window` o diagnosticar HWND.
**Parámetros clave:** — (sin parámetros).
**Evitar:** Usar como árbol UIA — solo metadatos de ventana de nivel superior.
**Ejemplo:** `list_windows()`
**Relacionadas:** `set_target_window`, `focus_window`, `detect_framework`

### `focus_window`

**Qué hace:** Busca ventana por título parcial y la enfoca, minimiza, maximiza o restaura.
**Cuándo usarla:** Cambio puntual de foco cuando el target de sesión no cubre el caso (p. ej. modal sin target).
**Parámetros clave:** `title` / `window_title` (requerido), `action` (`focus`|`minimize`|`maximize`|`restore`, default `focus`).
**Evitar:** Reemplazar `set_target_window` en flujos largos — el target auto-focus es más consistente.
**Ejemplo:** `focus_window(title="Buscar", action="focus")`
**Relacionadas:** `set_target_window`, `restore_window`, `list_windows`

### `launch_app`

**Qué hace:** Lanza un ejecutable; por defecto reutiliza instancia existente (enfoca y cierra duplicados).
**Cuándo usarla:** Abrir app de prueba o recovery tras UIA stale.
**Parámetros clave:** `path` (req), `args`, `reuse` (default `true`), `replace` (default `false` — cierra todas y abre una nueva).
**Evitar:** Llamar en bucle sin `replace=true` cuando la app ya está abierta — acumula ventanas.
**Ejemplo:** `launch_app(path="calc.exe")`
**Relacionadas:** `wait_for_input_idle`, `invalidate_cache`, `set_target_window`
**Calculadora:** `reuse=true` enfoca la existente; `replace=true` solo cuando UIA está stale.

### `restore_window`

**Qué hace:** Desminimiza ventana por título parcial o `window_handle` (HWND).
**Cuándo usarla:** Cuando `check_session_status` reporta `target_minimized=true` antes de interactuar.
**Parámetros clave:** `window_title` / `title`, `window_handle` (alternativa a título).
**Evitar:** Interactuar UIA con ventana minimizada — muchos patterns fallan silenciosamente.
**Ejemplo:** `restore_window(window_title="Calculadora")`
**Relacionadas:** `check_session_status`, `focus_window`

### `virtual_desktop`

**Qué hace:** Crea, cambia o cierra escritorios virtuales de Windows para aislar la automatización.
**Cuándo usarla:** Trabajar en GUI sin interferir con el escritorio del usuario.
**Parámetros clave:** `action`: `create`, `switch_left`, `switch_right`, `close`.
**Evitar:** Olvidar `close` al terminar — deja escritorios huérfanos.
**Ejemplo:** `virtual_desktop(action="create")`
**Relacionadas:** `launch_app`, `list_windows`

---

## 3. Exploración — árbol de accesibilidad

### `find_element`

**Qué hace:** Busca un elemento por `name`, `role`, `automation_id` o `class_name`.
**Cuándo usarla:** Primera opción para localizar controles antes de actuar.
**Parámetros clave:** `automation_id` (exacto), `name` (parcial), `role`, `index`, `window_title`/`title`, `window_handle`, `tree_mode`, `include_offscreen`.
**Evitar:** Saltar a OCR/coords sin probar `automation_id` — la respuesta incluye `find_ms`/`total_ms` para diagnosticar lentitud.
**Ejemplo:** `find_element(automation_id="btnGuardar", window_title="AST")`
**Relacionadas:** `list_elements`, `discover_control_interaction`, `spy_inspect`
**Timing:** respuesta incluye `find_ms` / `total_ms` (ej. `find 120ms`).

### `find_all_elements`

**Qué hace:** Lista todos los matches con índice `[0]`, `[1]`, … para desambiguar duplicados.
**Cuándo usarla:** Varios controles con el mismo `automation_id` o `name`; usar índice en `click_element` / `read_element_by_index`.
**Parámetros clave:** `automation_id`, `name`, `role`, `window_title`/`title`, `window_handle`.
**Evitar:** Elegir índice a ciegas sin listar — el orden puede cambiar tras refresco de UI.
**Ejemplo:** `find_all_elements(automation_id="num1Button", window_title="Calculadora")`
**Relacionadas:** `read_element_by_index`, `click_element`, `find_element`

### `list_elements`

**Qué hace:** Lista elementos accesibles en una ventana con filtro opcional por `role`.
**Cuándo usarla:** Mapear pantalla; filtrar con `role="ComboBox"` antes de OCR.
**Parámetros clave:** `max_depth` (default **0** = auto/framework), `role`, `tree_mode`, `include_offscreen`, `adaptive_cluster` (default `true` — recorta outliers fuera del cluster dominante de controles), `window_title`/`title`, `window_handle`.
**Inteligencia espacial:** tras listar, infiere la banda donde se concentran los controles (`content_region` en header) y elimina nodos fuera de ese rango (sin reglas por app).
**Profundidad auto (max_depth=0):** uwp/winui 32 · wpf 24 · winforms 16 · qt 20 · electron/chromium 28 · java_swing 24 · win32 12 · unknown 20.
**Evitar:** ventanas enormes sin `role` si hay timeout — bajar con `max_depth=8`.
**Default:** header `depth=auto/uwp→32` (ejemplo).
**Exploración acotada:** `list_elements(max_depth=8)` · **árbol completo:** `max_depth=-1`.
**Ejemplo:** `list_elements(window_title="Calculadora", role="Button", max_depth=4)`
**Relacionadas:** `find_element`, `get_snapshot`, `spy_tree`, `ascii_ui_view`
**Notas:** dedupe por `automation_id` en overlays UWP; filtra nodos fuera de la ventana objetivo (PID + client rect). Header puede reportar `out-of-scope removed` (scope genérico, no por producto).

### `get_snapshot`

**Qué hace:** Árbol compacto JSON (`nodes`) de la ventana o `window_handle` (modal lookup).
**Cuándo usarla:** Vista DOM-like de la pantalla sin listar 100+ líneas planas; modales hijos por HWND.
**Parámetros clave:** `max_depth` (default 3), `role`, `window_title`/`title`, `window_handle`.
**Evitar:** `max_depth` muy alto en ventanas grandes — timeout o JSON enorme.
**Ejemplo:** `get_snapshot(window_title="Buscar", window_handle=123456, max_depth=4)`
**Relacionadas:** `list_elements`, `find_element`, `fill_form`

### `ascii_ui_view`

**Qué hace:** Recorre el árbol UIA de la ventana objetivo y dibuja un mapa ASCII simplificado: cajas con nombres/`automation_id`, claves accionables (`e1`, `e2`…), badges de tab (`①②`…), marco tipo “ojo” y `@` en el control con foco. Devuelve sidecar JSON con `elements[]` para planificar clics.
**Cuándo usarla:** Antes de planificar clics — overview espacial compacto en el chat (ej. Calculadora, formularios); alternativa liviana a screenshot para el agente.
**Parámetros clave:** `window_title`/`title`, `window_handle`, `width` (columnas, default **100**), `height` (filas, default **52**), `max_depth` (default **0** = automático), `role`, `min_pixels`, `detail` (`basic` | `full`), `tree_mode`, `include_offscreen` (default `false`), `unicode_box`, `layout_mode` (`legible` | `proportional` | `stretch`, default **legible** — cajas compactas por fila), `preserve_aspect` (legacy alias), `use_colors` (default **false** — sin ANSI en chat), `occlusion_prune` (default true), `ocr` (default false), `include_keys` (default **false**), `include_tab_index` (default **false**), `include_elements`, `include_legend`, `include_focus`.
**Evitar:** Sustituir `list_elements` cuando necesitás todos los campos UIA; con `ocr=false` no lee pixels — solo layout UIA. `ocr=true` es más lento (screenshot + OCR). Las claves `eN` son referencia del mapa — actuar con `click_element(automation_id=…)` del JSON.
**Ejemplo:** `ascii_ui_view(window_title="Calculadora")` — colores ANSI solo en terminal: `use_colors=true`.
**Relacionadas:** `list_elements`, `get_snapshot`, `ui_fingerprint`, `screenshot`

### `read_element`

**Qué hace:** Lee propiedades UIA de un elemento por `automation_id`/`name` con `index` opcional.
**Cuándo usarla:** Verify puntual de valor, enabled, patterns sin inspección Spy completa.
**Parámetros clave:** `automation_id`, `name`, `role`, `window_title`/`title`, `window_handle`, `index` (default 0).
**Evitar:** Leer tras cambio de modo sin `invalidate_cache` — valores stale en Calculadora científica/display.
**Ejemplo:** `read_element(automation_id="CalculatorResults", window_title="Calculadora")`
**Relacionadas:** `find_element`, `wait_for_condition`, `get_element_properties`

### `read_element_by_index`

**Qué hace:** Lee propiedades del match N devuelto por `find_all_elements`.
**Cuándo usarla:** Duplicados de `automation_id`; necesitás propiedades del segundo botón, no del primero.
**Parámetros clave:** `index` (0-based, req), mismos filtros que `find_all_elements` (`automation_id`, `name`, `role`, `window_handle`).
**Evitar:** Usar índice sin haber listado antes — puede ser stale tras cambio de UI.
**Ejemplo:** `read_element_by_index(index=1, automation_id="num1Button")`
**Relacionadas:** `find_all_elements`, `click_element`, `read_element`

### `get_focused_element`

**Qué hace:** Devuelve el elemento con foco de teclado actual.
**Cuándo usarla:** Antes de `type_text` — confirmar que el campo activo es el esperado.
**Parámetros clave:** — (sin parámetros).
**Evitar:** Asumir foco tras `click_element` sin verificar — modales o validaciones pueden robar foco.
**Ejemplo:** `get_focused_element()`
**Relacionadas:** `type_text`, `set_element_value`, `find_element`

### `element_at_point`

**Qué hace:** Devuelve el elemento UIA bajo coordenadas de pantalla (pick estilo Spy).
**Cuándo usarla:** Depuración tras clic manual; validar qué ve UIA en un pixel.
**Parámetros clave:** `x`, `y` (coordenadas de pantalla, requeridos).
**Evitar:** Usar como localizador principal — las coords cambian con DPI/resize.
**Ejemplo:** `element_at_point(x=640, y=400)`
**Relacionadas:** `highlight_element`, `spy_inspect`, `click`

### `get_element_properties`

**Qué hace:** Propiedades UIA extendidas de un elemento (estilo inspector).
**Cuándo usarla:** Necesitás patterns, bounding rect o estado más allá de `read_element`.
**Parámetros clave:** `name`, `automation_id`, o `x`/`y` (>=0), `window_title`/`title`.
**Evitar:** Repetir en cada paso del flujo — preferir `discover_control_interaction` para estrategia.
**Ejemplo:** `get_element_properties(automation_id="cboGrupo", window_title="AST")`
**Relacionadas:** `spy_inspect`, `discover_control_interaction`, `read_element`

### `discover_control_interaction`

**Qué hace:** Recomienda tools MCP y pasos a partir de role + patterns UIA en vivo (read/act/fallback).
**Cuándo usarla:** Antes de actuar en un control desconocido — no adivinar combo vs calendario vs edit.
**Parámetros clave:** `automation_id` (preferido), `name`, `window_title`/`title`, `x`/`y`, `include_children` (default true).
**Evitar:** Ignorar la estrategia devuelta e ir directo a `click` por coords.
**Ejemplo:** `discover_control_interaction(automation_id="cboGrupo")`
**Relacionadas:** `spy_inspect`, `list_control_items`, `repo_hints`

### `spy_inspect`

**Qué hace:** Inspección profunda (40+ campos UIA) vía sidecar Spy.
**Cuándo usarla:** Fase 3 exploración — ver patterns, `automation_id`, jerarquía real.
**Parámetros clave:** `name`, `automation_id`, `x`, `y`, `window_title`/`title`.
**Evitar:** Invocar si `check_session_status` reporta `spy_available=false` sin compilar sidecar.
**Ejemplo:** `spy_inspect(automation_id="Units1", window_title="Calculadora")`
**Relacionadas:** `get_element_properties`, `spy_tree`, `discover_control_interaction`

### `spy_tree`

**Qué hace:** Recorre el árbol UIA con detalle Spy (scoped a ventana objetivo).
**Cuándo usarla:** Exploración profunda cuando `list_elements` no alcanza; modales por HWND.
**Parámetros clave:** `mode`, `max_depth` (default **0** = auto por framework; **-1** = ilimitado), `visible_only`, `window_title`/`title`.
**Evitar:** `max_depth` alto en árboles WinForms enormes — usar `role` o `get_snapshot` acotado.
**Ejemplo:** `spy_tree(window_title="AST", mode="raw", max_depth=8)` — solo visibles: `visible_only=true`.
**Relacionadas:** `spy_inspect`, `list_elements`, `get_snapshot`
**Scope:** árbol limitado a la ventana objetivo (PID/HWND), no desktop completo.

### `ui_fingerprint`

**Qué hace:** Huella hash del layout UI actual para detectar cambios de pantalla.
**Cuándo usarla:** Antes/después de navegación para saber si la UI cambió sin diff visual.
**Parámetros clave:** `window_title` / `title` (opcional; default target o foreground).
**Evitar:** Usar como único verify post-acción — preferir `wait_for_condition` semántico.
**Ejemplo:** `ui_fingerprint(window_title="Calculadora")`
**Relacionadas:** `wait_for_change`, `observe_ui_tool`, `list_elements`

### `detection_health`

**Qué hace:** Estado de backends UIA/MSAA/JAB y conteo de elementos por backend.
**Cuándo usarla:** Diagnóstico cuando `find_element` falla o la app es híbrida (Electron/Java).
**Parámetros clave:** `window_title` / `title` (opcional).
**Evitar:** Asumir UIA disponible en apps custom paint sin revisar `recommended_order`.
**Ejemplo:** `detection_health(window_title="Calculadora")`
**Relacionadas:** `detect_framework`, `check_java_bridge`, `smart_find`

### `detect_framework`

**Qué hace:** Detecta toolkit (WinForms, WPF, UWP, Electron, etc.) y hints de automatización.
**Cuándo usarla:** Primera interacción con app nueva — define si priorizar UIA, OCR o repo.
**Parámetros clave:** `window_title` / `title` (opcional).
**Evitar:** Hardcodear reglas por framework en el agente — usar salida + `discover_control_interaction`.
**Ejemplo:** `detect_framework(window_title="Calculadora")`
**Relacionadas:** `detection_health`, `observe_ui_tool`, `set_target_window`

### `check_java_bridge`

**Qué hace:** Verifica prerequisitos Java Access Bridge (JAVA_HOME, pyjab) para Swing/AWT.
**Cuándo usarla:** Antes de automatizar apps Java cuando `detection_health` sugiere JAB.
**Parámetros clave:** — (sin parámetros).
**Evitar:** Reintentar UIA puro en apps Swing sin JAB configurado.
**Ejemplo:** `check_java_bridge()`
**Relacionadas:** `detection_health`, `detect_framework`

---

## 4. Espera y verificación UIA

### `wait_for_element`

**Qué hace:** Poll UIA hasta que aparece un control (`automation_id`, `name` o `role`).
**Cuándo usarla:** Tras abrir diálogo, navegar o esperar que un panel se monte en el árbol.
**Parámetros clave:** `automation_id`, `name`, `role`, `window_title`/`title`, `timeout_ms` (default 10000), `poll_ms` (default 100).
**Evitar:** Usar `sleep` fijo cuando conocés el id del control — es menos fiable.
**Ejemplo:** `wait_for_element(automation_id="gcGrillaActividades", window_title="Buscar", timeout_ms=15000)`
**Relacionadas:** `find_element`, `element_exists`, `wait_for_condition`

### `wait_for_condition`

**Qué hace:** Poll hasta que una propiedad UIA del control coincide con `expected_value`.
**Cuándo usarla:** Verify post-acción — display, combo value, enabled, selected, toggle.
**Parámetros clave:** `property`, `expected_value` (req), `automation_id`, `name`, `role`, `window_title`/`title`, `timeout_ms`, `poll_ms`.
**Evitar:** Verify de display en Calculadora sin `invalidate_cache` tras cambio de modo — lectura stale.
**Ejemplo:** `wait_for_condition(property="name", automation_id="CalculatorResults", expected_value="Se muestra 7")`
**Relacionadas:** `invoke_element`, `click_element`, `read_element`
**Propiedades:** `name`, `isEnabled`, `isOffscreen`, `visible`, `text`, `value`, `isChecked`, `isSelected`, `selectedItem`.

### `wait_for_input_idle`

**Qué hace:** `WaitForInputIdle` del proceso de la ventana objetivo (Windows).
**Cuándo usarla:** Tras `launch_app` o navegación pesada, antes del primer click.
**Parámetros clave:** `window_title`/`title`, `timeout_ms` (default 10000).
**Evitar:** Sustituir `wait_for_element` cuando esperás un control concreto, no solo idle del proceso.
**Ejemplo:** `wait_for_input_idle(window_title="Calculadora", timeout_ms=8000)`
**Relacionadas:** `launch_app`, `click_element`, `check_session_status`

### `element_exists`

**Qué hace:** Comprueba una vez si un control existe (sin poll).
**Cuándo usarla:** Ramas condicionales; si puede tardar en aparecer, usar `wait_for_element`.
**Parámetros clave:** `automation_id`, `name`, `role`, `window_title`/`title`.
**Evitar:** Verify post-acción inmediata — la UI puede no haberse actualizado aún.
**Ejemplo:** `element_exists(automation_id="HistoryFlyout", window_title="Calculadora")`
**Relacionadas:** `wait_for_element`, `find_element`
**Respuesta:** `OK exists …` o `NOT FOUND …`.

---

## 5. Sesión y caché

### `check_session_status`

**Qué hace:** JSON de sesión: target, HWND vivo, escritorio bloqueado, ventana minimizada, `operations_available`, spy sidecar.
**Cuándo usarla:** Inicio de flujo largo o diagnóstico tras error UIA/input.
**Parámetros clave:** `window_title` (opcional; default `get_target_window`).
**Evitar:** Ignorar `target_minimized=true` o `session_locked=true` — las tools fallarán sin mensaje claro.
**Ejemplo:** `check_session_status()`
**Relacionadas:** `get_target_window`, `restore_window`, `release_all`

### `invalidate_cache`

**Qué hace:** Limpia cachés UIA tras relaunch, cambio de modo Calculadora o lecturas stale.
**Cuándo usarla:** Tras `launch_app(replace=true)`, error stale, verify incoherente en display.
**Parámetros clave:** `window_title`/`title` (opcional), `hwnd` (opcional, scope por ventana).
**Evitar:** Invalidar en cada paso — penaliza performance; solo tras cambio estructural.
**Ejemplo:** `invalidate_cache(window_title="Calculadora")`
**Relacionadas:** `check_session_status`, `launch_app`, `list_elements`

### `release_all`

**Qué hace:** Limpia target, cachés UIA, highlight y monitores de eventos activos.
**Cuándo usarla:** Fin de sesión de automatización o recovery total entre apps.
**Parámetros clave:** — (sin parámetros).
**Evitar:** Olvidar `stop_event_monitor`/`stop_watcher` antes si necesitás conservar logs — `release_all` los detiene.
**Ejemplo:** `release_all()`
**Relacionadas:** `set_target_window("")`, `stop_event_monitor`, `clear_highlight`

---

## 6. Formularios

### `fill_form`

**Qué hace:** Rellena varios campos en una llamada (`fields_json` array u objeto `{id: value}`).
**Cuándo usarla:** Formularios WinForms largos (Time Report, AST) — más rápido que N `set_element_value`.
**Parámetros clave:** `fields_json` / `fields` (req), `window_title`/`title`, `window_handle` (modal hijo).
**Evitar:** Combos dropdown — usar `select_control_item`; `fill_form` no verifica read-back en combos.
**Ejemplo:** `fill_form(fields_json='[{"automation_id":"txtHoras","value":"8"}]', window_title="AST")`
**Relacionadas:** `get_all_values`, `set_element_value`, `select_control_item`

### `get_all_values`

**Qué hace:** Lee todos los campos editables visibles (Edit, ComboBox, CheckBox…) como JSON.
**Cuándo usarla:** Verify de formulario completo sin N lecturas puntuales.
**Parámetros clave:** `window_title`/`title`, `window_handle`, `max_depth` (default 12).
**Evitar:** Asumir que incluye celdas de grilla — solo campos de formulario editables.
**Ejemplo:** `get_all_values(window_title="AST")`
**Relacionadas:** `fill_form`, `read_element`, `wait_for_condition`

### `set_element_value`

**Qué hace:** Escribe valor vía `ValuePattern` en campos de texto editables.
**Cuándo usarla:** Edit/SearchBox donde `ValuePattern` está soportado.
**Parámetros clave:** `value` (req), `automation_id`, `name`, `window_title`/`title`, `index`, `window_handle`.
**Evitar:** ComboBox dropdown — usar `select_control_item` (nunca `set_value` en combos UWP/WinForms).
**Ejemplo:** `set_element_value(automation_id="txtComentario", value="revisión", window_title="AST")`
**Relacionadas:** `fill_form`, `type_text`, `select_control_item`

---

## 7. Eventos UIA

### `start_event_monitor`

**Qué hace:** Inicia monitoreo de eventos UIA (`focus`, `structurechanged`, `propertychanged`).
**Cuándo usarla:** Diálogos async, carga de grillas, verify de actualización UI sin poll manual.
**Parámetros clave:** `event_type`, `automation_id`, `name`, `window_title`/`title`, `window_handle`, `poll_ms` (solo backend `poll`).
**Evitar:** Sustituir `wait_for_condition` / `invoke_element` con `verify_*` en verifies simples.
**Ejemplo:** `start_event_monitor(event_type="focus", window_title="Calculadora")`
**Relacionadas:** `get_event_log`, `stop_event_monitor`, `wait_for_condition`
**Backend:** `flaui_native` vía `awdui-event-sidecar` (AddAutomationEventHandler); fallback `poll`.

### `stop_event_monitor`

**Qué hace:** Detiene una sesión de monitoreo (o todas si `session_id` vacío).
**Cuándo usarla:** Al cerrar flujo async; siempre antes de cambiar de app o en cleanup.
**Parámetros clave:** `session_id` (vacío = detener todas las sesiones).
**Evitar:** Dejar sesiones abiertas entre tests — handlers UIA nativos o threads poll.
**Ejemplo:** `stop_event_monitor(session_id="abc123")`
**Relacionadas:** `start_event_monitor`, `release_all`

### `get_event_log`

**Qué hace:** Devuelve eventos UIA capturados de una sesión de monitoreo.
**Cuándo usarla:** Tras actuar, para consumir eventos de `start_event_monitor`.
**Parámetros clave:** `session_id` (vacío = agregar de todas), `max_count` (1–500, default 100).
**Evitar:** Polling agresivo en bucle — espaciar lecturas; el log no reemplaza verify semántico.
**Ejemplo:** `get_event_log(session_id="abc123", max_count=50)`
**Relacionadas:** `start_event_monitor`, `stop_event_monitor`

---

## 8. Acción UIA — patterns sin coordenadas

### `click_element`

**Qué hace:** Busca y activa el control (Invoke → SelectionItem → Toggle → click UIA → coords según config).
**Cuándo usarla:** Cuando `invoke_element` no alcanza o se necesita clic físico en el bbox.
**Parámetros clave:** `automation_id`, `name`, `role`, `window_title`/`title`, `index`, `window_handle`, `capture`, `verify_automation_id`, `verify_name_contains`, `verify_timeout_ms` (5000), `verify_poll_ms` (100).
**Evitar:** Clic por coords si el control tiene `InvokePattern` — más lento y frágil.
**Ejemplo:** `click_element(automation_id="num7Button", verify_automation_id="CalculatorResults", verify_name_contains="7")`
**Relacionadas:** `invoke_element`, `find_element`, `wait_for_condition`
**Verify:** con `verify_*` hace poll UIA hasta match. **Timing:** `total_ms` con `find_ms` + `act_ms` + `verify_ms`; `>=3000ms` -> SLOW.

### `invoke_element`

**Qué hace:** Activa controles UIA: `InvokePattern`, `SelectionItemPattern`, `TogglePattern`, `ExpandCollapse.Expand`.
**Cuándo usarla:** Botones, NavView, flyouts, toggles; verify integrado con `verify_*`.
**Parámetros clave:** `automation_id`, `name`, `window_title`/`title`, `verify_automation_id`, `verify_name_contains`, `verify_timeout_ms`, `verify_poll_ms`.
**Evitar:** Verify en el botón actuado cuando el display es otro control — pasar `verify_automation_id` explícito.
**Ejemplo:** `invoke_element(automation_id="equalButton", verify_automation_id="CalculatorResults", verify_name_contains="Se muestra 7")`
**Relacionadas:** `click_element`, `expand_element`, `wait_for_condition`
**Verify display:** si el botón actuado no es el display, pasar `verify_automation_id` explícito o `agent_hints` en repo.

### `expand_element`

**Qué hace:** Expande o colapsa vía `ExpandCollapsePattern`; `fallback_click` para expanders UWP sin pattern.
**Cuándo usarla:** ComboBox UWP (`Units1`), TreeItem; Configuración `AppThemeExpander` / `AboutExpander`.
**Parámetros clave:** `automation_id`, `name`, `window_title`/`title`, `action` (`expand`|`collapse`), `fallback_click` (bool, default false).
**Evitar:** `fallback_click` en ítems de lista/combo — solo headers tipo `SettingsExpander`.
**Ejemplo:** `expand_element(automation_id="AppThemeExpander", window_title="Calculadora", fallback_click=true)`
**Relacionadas:** `list_control_items`, `select_control_item`, `invoke_element`
**Settings:** `fallback_click=true` — fast-path HeaderClick directo (~<1s), salta cadena ExpandCollapse.

### `list_control_items`

**Qué hace:** Lista ítems bajo ComboBox, List o grid (`Table`/`DataGrid`) — subtree acotado, paginado.
**Cuándo usarla:** Antes de `select_control_item`; filtrar combos largos con `filter_text`.
**Parámetros clave:** `automation_id` (req), `filter_text`, `window_title`/`title`, `offset`, `limit` (default 50), `expand` (default true).
**Evitar:** OCR del dropdown abierto si UIA devuelve ítems — agotar esta tool primero.
**Ejemplo:** `list_control_items(automation_id="cboGrupo", filter_text="homologacion", window_title="AST")`
**Relacionadas:** `select_control_item`, `expand_element`, `read_table`
Fallback Win32 `ComboLBox` para WinForms sin hijos UIA. Combos UWP: `expand_element` primero si devuelve 0 ítems.

### `select_control_item`

**Qué hace:** Selecciona ítem por substring; nunca `set_value` en ComboBox dropdown; verifica read-back.
**Cuándo usarla:** Combos, listas y grillas lookup (con `double_click=true` en modales).
**Parámetros clave:** `automation_id` (req), `value` (req), `window_title`/`title`, `double_click`, `column` (grids DevExpress).
**Evitar:** `set_element_value` en combos — rompe dropdown UWP y no verifica selección.
**Ejemplo:** `select_control_item(automation_id="gcGrillaActividades", value="108082", double_click=true, window_title="Buscar")`
**Relacionadas:** `list_control_items`, `expand_element`, `click`
WinForms ComboLBox puede devolver `requires_operation=click` + `click_at` — llamar `click()` en esas coords.

### `get_grid_item`

**Qué hace:** Lee una celda de `Table`/`DataGrid` por índice fila/columna sin recorrer todo el árbol.
**Cuándo usarla:** Grillas DevExpress (AST) o grids UIA con `GridPattern`.
**Parámetros clave:** `automation_id` (grid, req), `row` (0-based), `column` (0-based), `column_name` (DevExpress ej. `titulo`), `window_title`/`title`.
**Evitar:** N llamadas celda a celda cuando necesitás la grilla entera — usar `read_table`.
**Ejemplo:** `get_grid_item(automation_id="gcGrillaActividades", row=0, column_name="titulo", window_title="AST")`
**Relacionadas:** `read_table`, `select_control_item`, `list_control_items`
**Estrategia:** `GridPattern.GetItem` → fallback ensamblado `DataItem` (`titulo row N`).

### `read_table`

**Qué hace:** Lee grilla completa como JSON `{headers, rows}` alineado con columnas.
**Cuándo usarla:** Exportar/verificar grilla AST o `Table`/`DataGrid` sin N `get_grid_item`.
**Parámetros clave:** `automation_id` (req), `filter_text`, `window_title`/`title`, `offset`, `limit` (default 200, max 500).
**Evitar:** `limit` bajo sin paginar con `offset` en grillas grandes.
**Ejemplo:** `read_table(automation_id="gcGrillaActividades", filter_text="108082", window_title="Buscar")`
**Relacionadas:** `get_grid_item`, `list_control_items`, `select_control_item`
**Respuesta:** JSON con `source`, `row_count`, `total_rows`, `has_more`.

### `scroll_into_view`

**Qué hace:** Trae un ítem al viewport visible vía `ScrollItemPattern.ScrollIntoView`.
**Cuándo usarla:** ListItem/TreeItem/DataItem fuera de pantalla en lista virtualizada o grilla.
**Parámetros clave:** `automation_id` (ítem, req), `window_title`/`title`.
**Evitar:** Coords de scroll manual si el ítem expone `ScrollItemPattern`.
**Ejemplo:** `scroll_into_view(automation_id="ListItem42", window_title="Calculadora")`
**Relacionadas:** `realize_virtualized_item`, `scroll_element`, `select_control_item`

### `realize_virtualized_item`

**Qué hace:** Materializa ítem virtualizado vía `VirtualizedItemPattern.Realize`.
**Cuándo usarla:** Lista UWP/WinUI larga donde el ítem no existe en el árbol hasta realizarse.
**Parámetros clave:** `automation_id` (ítem o placeholder, req), `window_title`/`title`.
**Evitar:** `select_control_item` directo en listas virtualizadas sin scroll/realize previo.
**Ejemplo:** `realize_virtualized_item(automation_id="HistoryListItem", window_title="Calculadora")`
**Relacionadas:** `scroll_element`, `scroll_into_view`, `select_control_item`
**Secuencia típica:** `scroll_element` → `realize_virtualized_item` → `select_control_item`.

### `find_item_by_property`

**Qué hace:** Busca hijo en lista/árbol con `ItemContainerPattern.FindItemByProperty`; fallback subtree.
**Cuándo usarla:** Listas grandes; buscar por `name` o `automation_id` con paginación.
**Parámetros clave:** `container_automation_id` (req), `property_name` (`name`|`automation_id`), `property_value` (req), `start_after_automation_id`, `window_title`/`title`.
**Evitar:** `list_elements` sin filtro en contenedores con miles de nodos.
**Ejemplo:** `find_item_by_property(container_automation_id="HistoryList", property_name="name", property_value="2+2=4")`
**Relacionadas:** `find_element`, `list_control_items`, `scroll_element`

### `scroll_element`

**Qué hace:** Desplaza contenedor con scroll vía `ScrollPattern.Scroll` o `SetScrollPercent`.
**Cuándo usarla:** Pane/List/Tree/DataGrid con barras de scroll UIA.
**Parámetros clave:** `automation_id` (req), `direction` (`up`|`down`|`left`|`right`), `amount` (`large`|`small`), `repeat`, o `horizontal_percent`/`vertical_percent` (>=0 activa SetScrollPercent).
**Evitar:** Confundir con `scroll` (rueda en coords) — esta tool usa pattern UIA.
**Ejemplo:** `scroll_element(automation_id="HistoryList", direction="down", amount="large", repeat=2)`
**Relacionadas:** `scroll_into_view`, `realize_virtualized_item`, `list_control_items`

---

## 9. Input por coordenadas y teclado

### `click`

**Qué hace:** Clic en coordenadas de pantalla con botón y cantidad configurables.
**Cuándo usarla:** Fallback cuando UIA falla; canvas; botones sin Invoke; tras `requires_operation=click` de combo WinForms.
**Parámetros clave:** `x`, `y` (req), `button` (`left`|`right`|`middle`), `clicks`, `capture`, `capture_full`.
**Evitar:** Coords hardcodeadas sin `set_target_window` — el scope bloquea clics fuera de la app objetivo.
**Ejemplo:** `click(x=512, y=384, button="left", clicks=1)`
**Relacionadas:** `click_element`, `highlight_element`, `find_text`

### `type_text`

**Qué hace:** Escribe texto carácter a carácter con teclado simulado.
**Cuándo usarla:** Tras foco confirmado en campo; fallback si `set_element_value` falla.
**Parámetros clave:** `text` (req), `interval` (segundos entre teclas, default 0.02).
**Evitar:** Escribir sin `get_focused_element` — el texto puede ir al terminal o ventana equivocada.
**Ejemplo:** `type_text(text="homologacion", interval=0.03)`
**Relacionadas:** `send_keys`, `set_element_value`, `get_focused_element`

### `send_keys`

**Qué hace:** Envía atajos y teclas especiales (`enter`, `ctrl+s`, `alt+down`).
**Cuándo usarla:** Navegación por teclado, confirmar diálogos, abrir combos con Alt+Down.
**Parámetros clave:** `keys` (req) — nombre de tecla o combo unido con `+`.
**Evitar:** Sustituir `invoke_element` en botones con UIA estable.
**Ejemplo:** `send_keys(keys="alt+down")`
**Relacionadas:** `type_text`, `click_element`, `select_control_item`

### `scroll`

**Qué hace:** Scroll con rueda o PageUp/Down en coordenadas (x,y) de pantalla.
**Cuándo usarla:** Páginas web, áreas sin `ScrollPattern` UIA.
**Parámetros clave:** `x`, `y`, `direction` (req), `amount`, `pages`, `capture`, `capture_full`.
**Evitar:** Confundir con `scroll_element` — esta tool es input por mouse/teclado, no pattern UIA.
**Ejemplo:** `scroll(x=640, y=400, direction="down", pages=1)`
**Relacionadas:** `scroll_element`, `click`, `screenshot`

### `drag`

**Qué hace:** Arrastra desde una posición de pantalla a otra.
**Cuándo usarla:** Sliders, reordenar listas o gestos sin pattern UIA.
**Parámetros clave:** `from_x`, `from_y`, `to_x`, `to_y` (req), `capture` (opcional).
**Evitar:** Drag por coords si existe `ScrollPattern` / `TransformPattern` en el control.
**Ejemplo:** `drag(from_x=100, from_y=200, to_x=300, to_y=200)`
**Relacionadas:** `click`, `scroll_element`, `hover`

### `hover`

**Qué hace:** Mueve el cursor a una posición sin hacer clic.
**Cuándo usarla:** Revelar tooltips, menús hover, estados on-mouse-over.
**Parámetros clave:** `x`, `y` (coordenadas de pantalla, req).
**Evitar:** Sustituir `invoke_element` / patterns en controles con UIA estable.
**Ejemplo:** `hover(x=640, y=400)`
**Relacionadas:** `click`, `element_at_point`, `get_mouse_position`

### `get_mouse_position`

**Qué hace:** Devuelve la posición actual del cursor en pantalla.
**Cuándo usarla:** Depuración de coords; correlacionar con `element_at_point` tras clic manual.
**Parámetros clave:** — (sin parámetros).
**Evitar:** Usar como estrategia de localización — las coords no son estables.
**Ejemplo:** `get_mouse_position()`
**Relacionadas:** `element_at_point`, `click`, `hover`

---

## 10. OCR y búsqueda visual

### `find_text`

**Qué hace:** OCR dual (RapidOCR + Windows) — devuelve coordenadas de matches.
**Cuándo usarla:** Contenido invisible a UIA (web, custom paint, labels sin automation_id).
**Parámetros clave:** `query` (req), `case_sensitive`, `window_title`/`title`, `near_y` (desambiguar por proximidad vertical).
**Evitar:** OCR si `list_elements` o grilla UIA ya tienen el dato — más lento y frágil.
**Ejemplo:** `find_text(query="Guardar", window_title="AST", near_y=300)`
**Relacionadas:** `click_text`, `smart_find`, `detect_visual_regions`

### `click_text`

**Qué hace:** OCR + clic en el match; reintenta offsets si no hay cambio visual.
**Cuándo usarla:** Último recurso cuando `click_element` y `invoke_element` fallan.
**Parámetros clave:** `query` (req), `occurrence` (default 1), `case_sensitive`, `window_title`/`title`, `near_y`, `capture`, `capture_full`.
**Evitar:** Clic OCR en botones que UIA ya localiza — rompe con cambio de tema/DPI.
**Ejemplo:** `click_text(query="Aceptar", window_title="Buscar", occurrence=1)`
**Relacionadas:** `find_text`, `click`, `smart_find`

### `smart_find`

**Qué hace:** Cascada UIA → repositorio → template → OCR dual → visual → agentic.
**Cuándo usarla:** Control desconocido; exploración con fallback automático.
**Parámetros clave:** `name` (req), `role`, `window_title`/`title`, `index`, `repo_path`, `agentic`, `highlight`.
**Evitar:** Usar en cada paso de un flujo estable — reservar para discovery.
**Ejemplo:** `smart_find(name="Historial", window_title="Calculadora", highlight=true)`
**Relacionadas:** `find_element`, `find_text`, `repo_find`

### `detect_visual_regions`

**Qué hace:** Detecta regiones clicables vía OpenCV + OCR en captura de ventana.
**Cuándo usarla:** Apps opacas a UIA; complemento a `observe_ui_tool`.
**Parámetros clave:** `window_title` / `title` (opcional; default target).
**Evitar:** Sustituir árbol UIA en WinForms/WPF donde `list_elements` funciona.
**Ejemplo:** `detect_visual_regions(window_title="Calculadora")`
**Relacionadas:** `find_text`, `build_detection_context`, `smart_find`

### `find_by_template_tool`

**Qué hace:** Busca imagen template (icono/botón) en la ventana con umbral configurable.
**Cuándo usarla:** Controles sin texto ni automation_id pero con icono estable.
**Parámetros clave:** `image_path` (req), `window_title`/`title`, `threshold` (default 0.75), `highlight`.
**Evitar:** Templates capturados en otro DPI/resolución — falsos negativos.
**Ejemplo:** `find_by_template_tool(image_path="assets/calc_menu.png", window_title="Calculadora", threshold=0.8)`
**Relacionadas:** `smart_find`, `highlight_element`, `screenshot`

---

## 11. Screenshots

### `screenshot`

**Qué hace:** Captura pantalla, ventana objetivo o región con anotaciones opcionales.
**Cuándo usarla:** Evidencia visual; UWP con `scope=window` (bbox visual incluye chrome).
**Parámetros clave:** `scope` (`auto`|`window`|`full`), `window_title`/`title`, `monitor`, `region_x/y/w/h`, `annotate`.
**Evitar:** `scope=full` cuando solo necesitás la app — incluye terminal y ruido.
**Ejemplo:** `screenshot(scope="window", window_title="Calculadora", annotate=true)`
**Relacionadas:** `wait_for_change`, `screenshot_baseline`, `highlight_element`
**Nota UWP:** `scope=window` usa rect visual de ventana (title chrome incluido).

### `wait_for_change`

**Qué hace:** Espera cambio visual en región (diff de píxeles) o timeout.
**Cuándo usarla:** Último recurso visual cuando UIA no expone el estado.
**Parámetros clave:** `timeout`, `threshold`, `poll_interval`, `monitor`, `region_x`, `region_y`, `region_w`, `region_h`.
**Evitar:** Verify semántico — preferir `wait_for_condition` / `wait_for_element`.
**Ejemplo:** `wait_for_change(timeout=5.0, threshold=0.01, region_x=100, region_y=100, region_w=400, region_h=300)`
**Relacionadas:** `screenshot`, `wait_for_condition`, `screenshot_diff`

### `get_screen_size`

**Qué hace:** Devuelve dimensiones de todos los monitores conectados.
**Cuándo usarla:** Calcular coords relativas, regiones OCR o validar multi-monitor.
**Parámetros clave:** — (sin parámetros).
**Evitar:** Asumir monitor primario único en setups multi-monitor.
**Ejemplo:** `get_screen_size()`
**Relacionadas:** `screenshot`, `click`, `find_text`

### `screenshot_baseline`

**Qué hace:** Captura baseline para comparación visual posterior con `screenshot_diff`.
**Cuándo usarla:** Antes de una acción cuyo efecto visual querés medir.
**Parámetros clave:** `monitor`, `region_x`, `region_y`, `region_w`, `region_h`.
**Evitar:** Baseline con ventana en distinto estado (minimizada, otro modo Calculadora).
**Ejemplo:** `screenshot_baseline(monitor=1)`
**Relacionadas:** `screenshot_diff`, `screenshot`, `wait_for_change`

### `screenshot_diff`

**Qué hace:** Compara pantalla actual contra baseline almacenado; overlay de píxeles cambiados.
**Cuándo usarla:** Verify visual post-acción cuando UIA no alcanza.
**Parámetros clave:** `threshold` (sensibilidad 0.0–1.0, default 0.02).
**Evitar:** Diff sin `screenshot_baseline` previo en la misma región/monitor.
**Ejemplo:** `screenshot_diff(threshold=0.02)`
**Relacionadas:** `screenshot_baseline`, `wait_for_change`

---

## 12. Repositorio de objetos (QTP/UFT)

### `repo_find`

**Qué hace:** Resuelve objeto lógico del repositorio estilo UFT (ej. `frmMain/btnSave`).
**Cuándo usarla:** Flujos con objetos ya capturados; localización estable por path.
**Parámetros clave:** `repo_path` (req), `window_title`/`title`, `highlight`.
**Evitar:** Capturar sin `repo_capture` previo — el path no existirá.
**Ejemplo:** `repo_find(repo_path="Calculadora/num7Button", highlight=true)`
**Relacionadas:** `repo_action`, `repo_hints`, `smart_find`

### `repo_list`

**Qué hace:** Lista objetos almacenados en el repositorio de la app activa.
**Cuándo usarla:** Ver qué controles ya están mapeados antes de `repo_action`.
**Parámetros clave:** `window_title` / `title` (opcional).
**Evitar:** Asumir repo vacío = app no automatizable — capturar con `repo_capture`.
**Ejemplo:** `repo_list(window_title="Calculadora")`
**Relacionadas:** `repo_find`, `repo_capture`, `repo_hints`

### `repo_hints`

**Qué hace:** Devuelve `agent_hints` de un objeto repo o lista hints de toda la app.
**Cuándo usarla:** Verify post-act con `verify_automation_id` documentado en repo (ej. display Calculadora).
**Parámetros clave:** `repo_path` (vacío = listar todos con hints), `window_title`/`title`.
**Evitar:** Ignorar hints de verify — evitan verify en control equivocado tras tecla.
**Ejemplo:** `repo_hints(repo_path="Calculadora/equalButton")`
**Relacionadas:** `invoke_element`, `discover_control_interaction`, `repo_find`

### `repo_action`

**Qué hace:** Ejecuta métodos Swf* (`Click`, `Set`, `Select`, `Expand`, `GetItem`, etc.) sobre objeto repo.
**Cuándo usarla:** Flujos con objetos capturados; abstrae patterns por clase Swf.
**Parámetros clave:** `repo_path` (req), `method` (req), `value`, `property_name`, `window_title`/`title`, `highlight`.
**Evitar:** Método no permitido para la clase Swf — revisar `allowed_methods` en error.
**Ejemplo:** `repo_action(repo_path="Calculadora/num7Button", method="Click")`
**Relacionadas:** `repo_find`, `invoke_element`, `click_element`

### `repo_capture`

**Qué hace:** Captura control al repositorio con clase Swf* y Smart ID (estilo Object Spy).
**Cuándo usarla:** Fase de mapeo — persistir localizador estable para flujos repetibles.
**Parámetros clave:** `repo_path` (req), `window_title`/`title`, `x`/`y`, `name`, `automation_id`, `parent`.
**Evitar:** Capturar overlay/transitorio (flyout cerrado) — el repo queda stale.
**Ejemplo:** `repo_capture(repo_path="Calculadora/sinButton", automation_id="sinButton", window_title="Calculadora")`
**Relacionadas:** `repo_find`, `spy_inspect`, `highlight_element`

---

## 13. Descubrimiento guiado

### `observe_ui_tool`

**Qué hace:** Observación inicial acotada: framework, árbol, modales, fingerprint, screenshot.
**Cuándo usarla:** Solo exploración — no en cada paso de ejecución.
**Parámetros clave:** `window_title`/`title`, `hints` (csv de pistas para el observer).
**Evitar:** Llamar en bucle dentro de un flujo productivo — depth 8, max 80 elementos.
**Ejemplo:** `observe_ui_tool(window_title="Calculadora", hints="modo científico,menú")`
**Relacionadas:** `plan_probes_tool`, `discover_target_tool`, `build_detection_context`

### `plan_probes_tool`

**Qué hace:** Lista rankeada de probes de revelación con razones (metódico, no aleatorio).
**Cuándo usarla:** Tras `observe_ui_tool` cuando la UI objetivo está oculta (menús, flyouts).
**Parámetros clave:** `goal` (req), `window_title`/`title`, `hints`, `expected_window`, `image_path`, `safe_mode` (default true).
**Evitar:** Probes sin goal claro — devuelve lista vacía o irrelevante.
**Ejemplo:** `plan_probes_tool(goal="abrir historial", window_title="Calculadora", safe_mode=true)`
**Relacionadas:** `apply_probe_tool`, `observe_ui_tool`, `discover_target_tool`

### `apply_probe_tool`

**Qué hace:** Aplica un probe de revelación (expand menú, scroll, access key, etc.).
**Cuándo usarla:** Ejecutar un probe del plan para exponer UI oculta.
**Parámetros clave:** `probe_id` (req), `target`, `window_title`/`title`, `hints` (csv), `safe_mode`.
**Evitar:** Probes aleatorios sin `observe_ui_tool` / plan previo.
**Ejemplo:** `apply_probe_tool(probe_id="expand_menu", target="Historial", window_title="Calculadora")`
**Relacionadas:** `plan_probes_tool`, `observe_ui_tool`, `discover_target_tool`

### `discover_target_tool`

**Qué hace:** Bucle de descubrimiento: observe → resolve → plan → apply probes hasta encontrar.
**Cuándo usarla:** Objetivo desconocido con hints; alternativa agentica a búsqueda manual.
**Parámetros clave:** `goal` (req), `window_title`/`title`, `hints`, `role`, `automation_id`, `image_path`, `repo_path`, `expected_window`, `max_steps`, `highlight_on_find`.
**Evitar:** `max_steps` alto sin supervisión — puede aplicar muchos probes.
**Ejemplo:** `discover_target_tool(goal="botón gráficas", window_title="Calculadora", max_steps=10)`
**Relacionadas:** `plan_probes_tool`, `smart_find`, `build_detection_context`

### `spy_walk_visible_tool`

**Qué hace:** Recorre elementos visibles resaltando cada uno (estilo Spy), paginado.
**Cuándo usarla:** Tour guiado de controles en pantalla nueva; enseñanza/diagnóstico.
**Parámetros clave:** `window_title`/`title`, `filter_role`, `start_index`, `batch_size` (default 10), `pause_ms` (default 800).
**Evitar:** Ejecutar en producción con `pause_ms` bajo — muchos highlights seguidos.
**Ejemplo:** `spy_walk_visible_tool(window_title="Calculadora", filter_role="Button", batch_size=5)`
**Relacionadas:** `spy_inspect`, `highlight_element`, `list_elements`

### `build_detection_context`

**Qué hace:** Contexto rico: screenshot + árbol + OCR dual + regiones visuales + sugerencias.
**Cuándo usarla:** Diagnóstico profundo cuando UIA y OCR simple no alcanzan.
**Parámetros clave:** `name`, `window_title` / `title`.
**Evitar:** En cada paso del flujo — es costoso (screenshot + OCR + árbol).
**Ejemplo:** `build_detection_context(name="Historial", window_title="Calculadora")`
**Relacionadas:** `observe_ui_tool`, `smart_find`, `detect_visual_regions`

---

## 14. Batch y utilidades

### `batch_actions`

**Qué hace:** Ejecuta secuencia de acciones en una llamada con screenshot opcional al final.
**Cuándo usarla:** Secuencias cortas conocidas (teclas calculadora) para reducir round-trips MCP.
**Parámetros clave:** `actions` (lista de dicts, req), `capture`, `capture_full`, `capture_scope`.
**Evitar:** Flujos largos sin verify intermedio — un fallo aborta toda la secuencia.
**Ejemplo:** `batch_actions(actions=[{"action":"click_element","automation_id":"num1Button"},{"action":"click_element","automation_id":"plusButton"},{"action":"wait","ms":200}])`
**Relacionadas:** `click_element`, `type_text`, `send_keys`
**Acciones válidas:** `click`, `click_element`, `type`, `keys`, `scroll`, `wait`.

### `clipboard`

**Qué hace:** Lee o escribe el portapapeles del sistema (`action=read|write`).
**Cuándo usarla:** Pegar datos externos o leer resultado copiado por la app.
**Parámetros clave:** `action` (req: `read`|`write`), `text` (solo para `write`).
**Evitar:** Clipboard como único verify — puede quedar contenido previo del usuario.
**Ejemplo:** `clipboard(action="write", text="108082")`
**Relacionadas:** `type_text`, `send_keys`

### `manage_screenshots`

**Qué hace:** Lista, limpia o ajusta el límite de screenshots guardados en sesión.
**Cuándo usarla:** Mantenimiento de disco tras sesiones largas con `capture=true`.
**Parámetros clave:** `action` (`list`|`cleanup`|`set_limit`), `keep` (para `set_limit`, default 50).
**Evitar:** `cleanup` si necesitás evidencia de un fallo reciente — borra archivos.
**Ejemplo:** `manage_screenshots(action="cleanup")`
**Relacionadas:** `screenshot`, `batch_actions`

### `highlight_element`

**Qué hace:** Resalta un elemento en pantalla con borde rojo (estilo Automation Spy).
**Cuándo usarla:** Debug visual; confirmar bbox antes de `click` por coords.
**Parámetros clave:** `name`, `automation_id`, `repo_path`, `x`/`y`, `window_title`/`title`, `duration_ms` (default 3000).
**Evitar:** Dejar highlight activo en screenshots — llamar `clear_highlight` antes.
**Ejemplo:** `highlight_element(automation_id="CalculatorResults", window_title="Calculadora", duration_ms=2000)`
**Relacionadas:** `clear_highlight`, `spy_inspect`, `click_element`

### `clear_highlight`

**Qué hace:** Elimina overlays de highlight en pantalla.
**Cuándo usarla:** Tras debug con `highlight_element` o antes de screenshot limpio.
**Parámetros clave:** — (sin parámetros).
**Evitar:** —
**Ejemplo:** `clear_highlight()`
**Relacionadas:** `highlight_element`, `spy_walk_visible_tool`, `screenshot`

---

## 15. Watcher de ventanas

### `start_watcher`

**Qué hace:** Monitorea en background ventanas, diálogos y toasts nuevos.
**Cuándo usarla:** Flujos que disparan modales async (guardar, confirmar, UAC).
**Parámetros clave:** `poll_interval` (default 1.0, min 0.2), `capture_snippets` (default true).
**Evitar:** Dejar watcher activo indefinidamente — consume polls y screenshots.
**Ejemplo:** `start_watcher(poll_interval=1.0, capture_snippets=true)`
**Relacionadas:** `get_notifications`, `stop_watcher`, `wait_for_element`

### `stop_watcher`

**Qué hace:** Detiene el watcher de notificaciones de ventanas.
**Cuándo usarla:** Cleanup al terminar flujo que usó `start_watcher`.
**Parámetros clave:** — (sin parámetros).
**Evitar:** Olvidar detener — `get_notifications` seguirá acumulando en memoria.
**Ejemplo:** `stop_watcher()`
**Relacionadas:** `start_watcher`, `get_notifications`, `release_all`

### `get_notifications`

**Qué hace:** Devuelve ventanas/diálogos/toasts detectados desde que inició el watcher.
**Cuándo usarla:** Tras acción que puede abrir modal; polling de eventos de ventana.
**Parámetros clave:** `clear` (default true — vacía cola tras leer).
**Evitar:** `clear=false` en bucle sin procesar — la cola crece.
**Ejemplo:** `get_notifications(clear=true)`
**Relacionadas:** `start_watcher`, `focus_window`, `wait_for_element`

---

## 16. Sistema y versión

### `configure_uac`

**Qué hace:** Gestiona prompts UAC para automatización elevada (`suppress`/`restore`/`status`).
**Cuándo usarla:** Apps que requieren elevación repetida; siempre `restore` al terminar.
**Parámetros clave:** `action` (req): `suppress`, `restore`, `status`.
**Evitar:** Dejar `suppress` activo — reduce seguridad del sistema.
**Ejemplo:** `configure_uac(action="status")`
**Relacionadas:** `launch_app`, `check_session_status`

### `check_version`

**Qué hace:** Consulta si hay release más nuevo de AwdUI en GitHub.
**Cuándo usarla:** Antes de reportar bugs o verificar que el MCP está actualizado.
**Parámetros clave:** `force` (bool, re-chequear remoto ignorando caché).
**Evitar:** —
**Ejemplo:** `check_version(force=true)`
**Relacionadas:** `get_server_info`

### `get_server_info`

**Qué hace:** Versión del servidor MCP, runtime, path y disponibilidad de update en GitHub.
**Cuándo usarla:** Diagnóstico de versión/path del servidor o update disponible.
**Parámetros clave:** — (sin parámetros).
**Evitar:** —
**Ejemplo:** `get_server_info()`
**Relacionadas:** `check_version`, `detection_health`

---

## Árbol de decisión rápido

```
¿Conocés automation_id?
  Sí → discover_control_interaction o spy_inspect (patterns)
       → seguir estrategia recomendada (invoke / expand / set_value)
  No → list_elements(role=…) o find_element
       → smart_find / find_text (último recurso)
```

---

## Changelog del catálogo

| Fecha | Cambio |
|-------|--------|
| 2026-09-06 | `list_elements`: cluster espacial adaptativo (`adaptive_cluster`, `content_region`); sin reglas por app. |
| 2026-09-06 | `max_depth=0`: profundidad adaptativa por framework (`tree_depth.py` + `detect_framework`); `-1` = ilimitado. |
| 2026-09-06 | **Regla diseño:** MCP agnóstico de app — eliminado `calculator_mode_filter`; ver `.cursor/rules/awdui-app-agnostic.mdc`. |
| 2026-09-06 | `set_target_window`: `focus_policy` minimal (default) / always / never — UIA sin robar foco; pointer/teclado solo si hace falta. |
| 2026-09-06 | `ascii_ui_view`: layout legible empaquetado por filas; cajas compactas; sin ANSI por defecto. |
| 2026-09-06 | `ascii_ui_view`: layout legible separa filas por gap horizontal y controles anchos; `use_colors` ANSI; default 80×36. |
| 2026-09-06 | `ascii_ui_view`: `preserve_aspect` → layout legible por filas/columnas (llena grilla, no escala ventana). |
| 2026-09-06 | `ascii_ui_view`: `preserve_aspect=true` (default) — escala uniforme bbox contenido (supersedido por layout legible). |
| 2026-09-06 | `ascii_ui_view`: `ocr=true` — RapidOCR ventana + ROI para controles sin nombre UIA. |
| 2026-09-06 | `ascii_ui_view`: árbol por contención + `occlusion_prune` (menos solapamiento). |
| 2026-09-06 | `ascii_ui_view`: legend keys (eN), tab badges (①②), role glyphs, `unicode_box`, sidecar JSON `elements[]`. |
| 2026-09-06 | Nueva `ascii_ui_view` — mapa ASCII de la ventana (ojo UI para agentes). |
| 2026-09-06 | Catálogo: revisión agentica completa — 86 secciones dedicadas con plantilla por tool. |
| 2026-09-06 | `start_event_monitor`: backend `flaui_native` vía `awdui-event-sidecar` (AddAutomationEventHandler); fallback `poll`. |
| 2026-09-06 | D1-D5 winapp: `fill_form`, `get_all_values`, `find_all_elements`, `read_element*`, `get_snapshot`, `window_handle` scope, `start_event_monitor`/`get_event_log`, `release_all`, `restore_window`, `check_session_status` enriquecido. |
| 2026-09-06 | Bloque C sesión: `invalidate_cache`, `element_exists`, `check_session_status`. |
| 2026-09-05 | `read_table` — grilla completa JSON `{headers, rows}` (Grid/Table UIA + DevExpress). |
| 2026-09-05 | Bloque A UIA: `scroll_into_view`, `realize_virtualized_item`, `find_item_by_property`, `scroll_element` (ScrollItem/VirtualizedItem/ItemContainer/Scroll patterns). |
| 2026-09-05 | `get_grid_item` — celda Table/DataGrid por fila/columna (GridPattern + fallback DevExpress). |
| 2026-09-05 | `invoke_element` / `click_element`: `verify_*` ahora hace poll UIA (`wait_for_condition` interno); `verify_timeout_ms` / `verify_poll_ms`. |
| 2026-09-05 | `wait_for_element`, `wait_for_condition`, `wait_for_input_idle` — espera semántica UIA (preferir sobre `wait_for_change`). |
| 2026-09-05 | `list_control_items` + `select_control_item` (combo/list/grid scoped; Win32 fallback; verify read-back). |
| 2026-09-05 | Nueva `discover_control_interaction` (role/patterns → tools genéricas); verify post-act usa `agent_hints` del repo en lugar de reglas por app. |
| 2026-09-05 | `expand_element`: fast-path con `fallback_click=true` (spy_inspect + HeaderClick, sin cadena ExpandCollapse). |
| 2026-09-05 | Nueva tool `expand_element` (ExpandCollapse); `invoke_element` incluye Expand en cadena. |
| 2026-09-05 | Sync índice con **59** tools reales; removidas entradas no implementadas; `invoke_element` SelectionItem/Toggle + `elapsed_ms`; gap ExpandCollapse documentado. |
| 2026-07-07 | `click_element` usa bbox de `highlight_element`; scope enforcement en `set_target_window`. |

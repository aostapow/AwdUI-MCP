# Teams — mapa UIA (TE-02 discovery en vivo)

> Completado 2026-09-06 TE-02. IDs dinámicos Electron/WebView — preferir `name` + role; compose `automation_id` es UUID por sesión.

## Ventana principal

| Campo | Valor observado TE-02 |
|-------|------------------------|
| Título ventana | `Chat \| {contacto} \| Microsoft Teams` (cambia con chat activo) |
| HWND / process | hwnd=132488; ms-teams.exe |
| Framework | **unknown** (detect_framework no clasifica Electron; class=TeamsWebView) |
| Client rect | ~1719×930 @126,16 |
| Root | Document id=RootWebArea; Group id=app |

## Nav rail (izquierda)

| ID lógico | name (ES) | role | automation_id | patterns |
|-----------|-----------|------|---------------|----------|
| NAV-ACTIVITY | Actividad (Ctrl+1) | Button | `14d6962d-6eeb-4f48-8890-de55454bb136` | Invoke |
| NAV-CHAT | Chat (Ctrl+2) | Button | `3b64df9d-7e97-4d9c-ac5c-2e0a5d8e6f40` | Invoke |
| NAV-CALENDAR | Calendario (Ctrl+3) | Button | `ef56c0de-36fc-4ef8-b417-3d82ba9d073c` | Invoke |
| NAV-CALLS | Llamadas (Ctrl+4) | Button | `20c3440d-c67e-4420-9f80-0e50c39693df` | Invoke |
| NAV-ONEDRIVE | OneDrive (Ctrl+5) | Button | `5af6a76b-40fc-4ba1-af29-8f49b08e44fd` | Invoke |
| NAV-COPILOT | Copilot (Ctrl+6) | Button | `b5abf2ae-c16b-4310-8f8a-d3bcdb52f162` | Invoke |
| NAV-PEOPLEHUB | PeopleHub (Ctrl+7) | Button | `97b67008-6dc4-442e-82d3-85d9f31c8aff` | Invoke |

**Nota:** UUIDs de nav pueden rotar entre builds; fallback `name` + atajo Ctrl+N.

## Búsqueda

| ID lógico | role | name | automation_id | atajo |
|-----------|------|------|---------------|-------|
| SEARCH-BOX | ComboBox | Presione Ctrl+G para ir directamente a un chat o canal | `ms-searchux-input` | Ctrl+G |

## Chat — Nicolás Awamori

| ID lógico | role | name / señal | automation_id | tool |
|-----------|------|--------------|---------------|------|
| CHAT-LIST-ITEM | TreeItem | Chat Awamori, Nicolas Sin conexión | `menur1eu` *(rotó menur1r→menur1eu 2026-09-07)* | invoke_element SelectionItem verify ~1163ms |
| CHAT-HEADER | ListItem | Awamori, Nicolas Sin conexión | `listItemrbd` | spy_inspect |
| COMPOSE-BOX | Edit | Escribe un mensaje | UUID dinámico `new-message-*` | `click_element` + `type_text`; verify **screenshot** (ValuePattern CKEditor stale) |
| SEND-BUTTON | Button | Enviar (Ctrl+Enter) | *(sin id en find)* | `invoke_element` name=Enviar (Ctrl+Enter) — TE-07 ~2368ms |
| MESSAGE-PANE | Group | message-pane-layout-a11y | `message-pane-layout-a11y` | scroll_element |

**Compose discovery:** `discover_control_interaction` → `set_element_value` (high); patterns Value + LegacyIAccessible.

## Tabs chat activo

| Tab | automation_id |
|-----|---------------|
| Chat | `com.microsoft.chattabs.chat` |
| Compartido | `com.microsoft.chattabs.files` |
| Notas | `com.microsoft.chattabs.chatnotes` |

## Equipos y canales (TE-09)

| ID lógico | role | name | automation_id | tool |
|-----------|------|------|---------------|------|
| TEAMS-SECTION | Button | Equipos y canales No leído… | *(sin id en find)* | invoke_element |
| CHAN-GENERAL | TreeItem | Equipos y canales Testing Accusys Canal General | `menurt3` *(rotó menurhl)* | invoke_element SelectionItem |
| NAV-CHAT-RETURN | Button | Chat (Ctrl+2) | `3b64df9d-7e97-4d9c-ac5c-2e0a5d8e6f40` | invoke_element TogglePattern |

**Nota TE-09:** canal General no expone compose `Escribe un mensaje`; botón **Publicar en el canal** — **prohibido** invocar. Título ventana cambia a `Chat | Testing Accusys | General | Microsoft Teams`.

## Calendario (TE-10)

| ID lógico | role | name | automation_id | tool |
|-----------|------|------|---------------|------|
| NAV-CALENDAR | Button | Calendario (Ctrl+3) | `ef56c0de-36fc-4ef8-b417-3d82ba9d073c` | invoke_element TogglePattern |
| CAL-TODAY | Button | Ir a hoy … | *(dinámico por fecha)* | invoke_element |
| CAL-VIEW | Button | Día / Semana | — | solo lectura harness |

Título ventana: `Calendar | Microsoft Teams`. Vista día con grid horario + mini-calendario. **No** invocar Nuevo/Reunirse ahora.

## Llamadas (TE-11)

| ID lógico | role | name | automation_id | tool |
|-----------|------|------|---------------|------|
| NAV-CALLS | Button | Llamadas (Ctrl+4) | `20c3440d-c67e-4420-9f80-0e50c39693df` | invoke_element TogglePattern |
| DIAL-COMBO | ComboBox | Llamadas | *(sin id)* | click_element ExpandCollapse |
| DIAL-CALL | Button | Llamar | — | **prohibido** invocar en harness |
| CALLS-MORE | Button | Más acciones | `menur1l5` | expand_element (menú historial) |

Título ventana: `Llamadas | Microsoft Teams`. Flujo TE-11: abrir marcador + nombre → **Escape** cancelar → **no** pulsar Llamar.

## Configuración / perfil (TE-12)

| ID lógico | role | name | automation_id | tool |
|-----------|------|------|---------------|------|
| PROFILE-AVATAR | Button | Tu perfil, estado… | `idna-me-control-avatar-trigger` | invoke_element ExpandCollapse |
| MORE-OPTIONS | Button | Configuración y más | `more-options-header` | invoke_element ExpandCollapse |
| SETTINGS-MENU | MenuItem | Configuración | — | invoke_element |
| SETTINGS-NAV | TabItem | Notificaciones y actividad / General / … | — | invoke_element SelectionItem |
| BACK | Button | Volver | `menur7o` | invoke_element (o nav Chat + Escape) |

Título ventana settings: `Chat | Configuración | Microsoft Teams`. **No** modificar toggles; solo lectura 1–2 secciones.

## Actividad (TE-13)

| ID lógico | role | name | automation_id | tool |
|-----------|------|------|---------------|------|
| NAV-ACTIVITY | Button | Actividad (Ctrl+1) | `14d6962d-6eeb-4f48-8890-de55454bb136` | invoke_element TogglePattern |
| ACT-HEADER | Text | Actividad | `feed-header` | spy_inspect |
| ACT-FILTER | ToolBar | Opciones de filtro | `upfront-filter-toolbar-id` | solo lectura |
| ACT-ITEM | Group | `{autor} mencionó…` | `activity-feed-item-title-{id}` | click/invoke **falla** InvokePattern — nav abre primer item |
| BACK | Button | Volver | `menur7o` | invoke_element ExpandCollapse → regresa Chat |

Título ventana actividad+item: `Actividad | {equipo/chat} | Microsoft Teams`. **No** enviar mensajes ni Publicar.

## Nuevo chat cancel (TE-14)

| ID lógico | role | name | automation_id | tool |
|-----------|------|------|---------------|------|
| NEW-ITEMS | Button | Nuevos elementos | `menur30a` | invoke_element ExpandCollapse |
| NEW-MSG | MenuItem | Nuevo mensaje | — | invoke_element InvokePattern |
| NEW-PARA | Edit | Para: Escribir nombre… | — | **no** seleccionar destinatario alternativo |
| CANCEL | — | Escape | — | **no** cierra en vivo; regresar `menur31g` Awamori TreeItem |

## Adjuntar cancel (TE-15)

| ID lógico | role | name | automation_id | tool |
|-----------|------|------|---------------|------|
| ATTACH | Button | Adjuntar archivos | — | invoke_element ExpandCollapse |
| UPLOAD-DEVICE | MenuItem | Cargar desde este dispositivo | — | invoke_element InvokePattern |
| PICKER | Window | Abrir | `#32770` | `set_target_window('Abrir')` scope modal |
| PICKER-CANCEL | Button | Cancelar | `2` | `click_element(name=Cancelar, scope_mode=auto, verify_modal_dismissed=true)` |
| REMOVE-ATTACH | Button | Quitar datos adjuntos | — | si queda chip accidental post-picker |

**Nota TE-15:** picker `Abrir` usa `msedgewebview2.exe` (PID ≠ Teams); `scope_mode=auto` resuelve modal #32770 foreground sin `set_target_window('Abrir')`. WebView2 fallback en `window_scope.py`.

## Emoji dismiss (TE-16)

| ID lógico | role | name | automation_id | tool |
|-----------|------|------|---------------|------|
| EMOJI-BTN | Button | Emoji, GIF y adhesivos | — | invoke_element ExpandCollapse |
| EMOJI-PANEL | — | tabs Todo / Emoji / GIF / Adhesivos | — | verify screenshot |
| EMOJI-SEARCH | Edit | Encuentra algo divertido | — | `element_exists` NOT FOUND post-Escape |
| DISMISS | — | Escape | — | `press_key` Escape — **no** seleccionar emoji/GIF/adhesivo |

## Atajos teclado (TE-17)

| ID lógico | atajo | efecto | verify |
|-----------|-------|--------|--------|
| SEARCH-GLOBAL | Ctrl+E | ComboBox «Busca rápidamente personas, mensajes y archivos» | `get_focused_element` |
| SEARCH-CLOSE | Escape | cierra overlay búsqueda | focus Document + screenshot |
| SEARCH-BOX | ComboBox | Búsqueda (Ctrl+E) | `ms-searchux-input` |

**Nota TE-17:** tabs filtro (Mensajes/Archivos/…) pueden quedar en árbol UIA offscreen post-Escape — verificar visualmente con screenshot.

## Recovery stale (TE-18)

| Nivel | acción | tool |
|-------|--------|------|
| L3 | invalidate + relaunch | `invalidate_cache`; `launch_app(%LOCALAPPDATA%\\Microsoft\\WindowsApps\\ms-teams.exe, replace=true)` |
| TE-01 | post-relaunch baseline | `set_target_window('Microsoft Teams')`; `detect_framework`; `list_windows` |
| Re-chat | Awamori | `find_element` TreeItem Awamori; `invoke_element` SelectionItem; `set_target_window('Awamori')` |
| Verify | harness msg | `find_text('[AwdUI-MCP-TE]')`; `get_tree_hash` |

**Nota TE-18:** hwnd rota (ej. 132488→263750); `wait_for_input_idle` puede FAIL pid post-relaunch; sesión Teams puede restaurar chat Awamori sin búsqueda.

## Session health (TE-19)

| Tool | expect TE-19 |
|------|----------------|
| `check_session_status` | `success=true`, `target_alive=true`, ops disponibles |
| `get_tree_hash` | hash estable post-recovery (ej. `37bb7ac5609ece91`, depth=6) |
| `detection_health` | backends uia/msaa/win32/jab/flaui OK |
| `check_version` | v0.4.0 up to date (opcional evidencia TE-00) |
| verify chat | `find_text('[AwdUI-MCP-TE]')` sin envío |

## Cierre sesión (TE-20)

| Paso | tool | expect |
|------|------|--------|
| OBS | `screenshot` | Chat Awamori + TE-07 visible |
| ACT | `set_target_window('')` | Target cleared |
| VERIFY | `get_target_window` + `check_session_status` | `target_set=false`, `mcp_server=true` |

**Nota:** matriz 21/21 `met` **≠** `teams_perfect` si quedan workarounds obligatorios (ver harness skill).

## Launch (TE-01)

| Método | Resultado |
|--------|-----------|
| `ms-teams:` | FAIL WinError 2 |
| `Teams.exe` | FAIL WinError 2 |
| Ruta completa | OK: `%LOCALAPPDATA%\Microsoft\WindowsApps\ms-teams.exe` |

## Notas discovery

- `list_elements role=TreeItem`: **~462ms** cold post scoped_out fix (turn9), **0ms** cache; **49** TreeItems incl. offscreen (`menur1g4` Reyes y=999). Turn6 baseline 3398ms antes de optimización scroll-merge + scope.
- **Virtualización sidebar (2026-09-07):** scroll-merge en `_collect_treeitem_findall` + **`filter_elements_to_scope(include_offscreen=True)`** conserva TreeItems sidebar aunque y>client (antes 33 scoped_out → solo 16 visibles).
- no usar `view_scope=true` en chats (5s+ walk del content pane). Compact-row filter elimina leak Cursor.
- `ascii_ui_view`: error `list index out of range` — gap MCP documentado.
- `ui_fingerprint`: 46249db9f0ce89bf (20 elements) vs observe 73/450 named.
- Screenshots con target background pueden capturar foreground (Cursor) — usar `focus_policy=always` en hitos visuales si aplica.

## Gaps MCP

→ [gaps/mcp-improvements.md](gaps/mcp-improvements.md)

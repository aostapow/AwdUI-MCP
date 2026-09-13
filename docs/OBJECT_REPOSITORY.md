# Object Repository (UFT-style / Swf*)

Logical object names are stored in **SQLite** at `~/.awdui-mcp/repository.db`.  
Image assets live in `~/.awdui-mcp/repository-assets/{app_id}/`.

Legacy JSON repos under `~/.awdui-mcp/repositories/` are migrated automatically on first access.

## Repo Studio (web UI)

```powershell
# Production: API serves built SPA on http://127.0.0.1:8765
& C:\mcps\AwdUI-MCP\scripts\start-repo-studio.ps1

# Development: API :8765 + Vite :5173
& C:\mcps\AwdUI-MCP\scripts\start-repo-studio.ps1 -Dev
```

Features:
- Tree explorer: App → Window → Object
- Inspector: full properties, QTP identification tiers (mandatory/assistive/smart)
- Agent hints editor (operational notes for the AI agent)
- Search by name, automation_id, repo_path
- **Catálogo MCP** — frameworks, controles UIA, métodos Swf* y resumen de objetos guardados (pestaña «Catálogo MCP» o `GET /api/catalog`)
- **Ayuda** — guía integrada: uso del repo, niveles UIA, tools MCP, mantenimiento (pestaña «Ayuda» en Repo Studio)

## Catálogo MCP (frameworks → objetos → métodos)

En Repo Studio, pestaña **Catálogo MCP**:

| Sección | Contenido |
|---------|-----------|
| **Frameworks** | UWP, WinForms, WPF, Electron, … con nivel UIA y hints de `detect_framework` |
| **Objetos Swf*** | Clases del repo (`SwfButton`, `SwfComboBox`, …) y métodos `repo_action` (Click, Set, Select, …) |
| **Controles UIA** | 40 tipos UIA — patterns Microsoft, tools de lectura y bindings de actuación (`invoke_element`, `select_control_item`, …) |
| **Tu repositorio** | Conteo de objetos capturados por framework y clase Swf |

API (misma data que la UI):

```http
GET http://127.0.0.1:8765/api/catalog
```

Fuente machine-readable: `mcp-servers/awdui-server/detection/data/uia_control_map.json` + `winforms_map.py`.

Documentación extendida: `.cursor/skills/awdui-mcp-automejora/references/patterns/control-catalog.md`

## Naming

| QTP / UFT | AwdUI repo_path |
|-----------|-------------------|
| `SwfWindow("frmMain").SwfButton("btnSave")` | `frmMain/btnSave` |
| `SwfWindow("frmMain").SwfPage("tabDatos").SwfEdit("txtNombre")` | `frmMain/tabDatos/txtNombre` |

## Swf* classes

WinForms and UIA controls use QTP-style classes (`SwfButton`, `SwfEdit`, …) with per-class identification profiles in `winforms_map.py`.

## MCP tools

| Tool | Purpose |
|------|---------|
| `repo_capture` | Object Spy → add control to repository |
| `repo_find` | Resolve logical name (Smart Identification) |
| `repo_action` | Execute Swf* method: `Click`, `Set`, `Select`, … |
| `repo_list` | List stored objects |
| `repo_hints` | Read agent hints for object or app |
| `smart_find` | Cascade including repo layer |

## Auto-capture

**Policy:** every automation target app persists controls on successful interaction when `set_target_window` matches the window (Calculator, Explorer, Teams, Edge, Notepad, etc.).

Auto-capture runs on successful `find_element` (`remember=true` default), and after successful **`click_element`**, **`invoke_element`**, and **`expand_element`** acts (upsert / update `last_resolution`). **`smart_find`** uses the same gate.

**Gates:**

1. **`set_target_window` is set** and the control's window title matches that target (substring match on title head).
2. Process is **not** in the exclusion list below.
3. Without an active target, nothing is auto-captured unless `AWDUI_AUTO_REPO=1` (legacy/dev).

**Excluded executables** (auto-capture only; `repo_capture` always allowed):

| Executable | Reason |
|------------|--------|
| `cursor.exe`, `code.exe`, `devenv.exe` | IDE / agent host |
| `node.exe`, `python.exe` | MCP / script runtime |
| `cmd.exe`, `powershell.exe`, `wt.exe`, `windowsterminal.exe` | Shells |
| `microsoft.cmdpal.ui.exe`, `powertoys.quickaccess.exe` | OS launcher overlays |
| `textinputhost.exe` | Windows touch keyboard |

**Explicit capture** via `repo_capture` is always allowed (any app).

Each allowed capture saves:
- Full detectable properties
- Identification tiers (mandatory / assistive / smart / ordinal)
- Last resolution (backend, bbox)
- Optional snapshots when `AWDUI_SNAPSHOT=1`

Objects are keyed by stable `repo_path` (e.g. `MyApp/frmMain/btnSave`).

## Agent hints (app-specific, not MCP code)

Store operational notes per object in `agent_hints` (Repo Studio or `repo_capture`). Plain text lines or JSON.

| Key | Purpose |
|-----|---------|
| `verify_automation_id` | After `invoke_element`/`click_element` on this control with `verify_name_contains`, read this other control instead (e.g. keypad → display) |
| `verify_target` | Alias of `verify_automation_id` |
| `note` | Free text for the agent |

Example (Calculadora lab — belongs in repo, not server code):

```
verify_automation_id: CalculatorResults
note: keypad buttons verify display text, not button name
```

`discover_control_interaction` and post-act verify read these hints when the acted `automation_id` matches a repo object.

## Auto repository lookup (Windows)

When `repo_path` is omitted, `smart_find`, `find_element`, and `click_element` **search the repository first**:

- Match by `automation_id`, logical name, digit → `numNButton`, or stored identification tiers
- Scoped to the target window when `window_title` is set
- On match, run Smart Identification (`mandatory` → `assistive` → `smart` → template → OCR)
- If repository resolution fails, continue the normal cascade (UIA → OCR → …)

Example: `smart_find(name="6", window_title="Calculadora")` resolves `Calculadora/num6Button` automatically when it exists in the repo.

## Smart Identification order

1. Mandatory properties only
2. Mandatory + assistive
3. Smart properties one-by-one
4. Ordinal index
5. Template image from last snapshot
6. OCR on stored visible text

## REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/apps` | GET | List applications |
| `/api/apps/{app_id}/tree` | GET | Window/object tree |
| `/api/objects?repo_path=` | GET | Object detail + hints |
| `/api/objects/{repo_path}` | PUT | Update identification / hints |
| `/api/search?q=` | GET | Search objects |
| `/api/migrate` | POST | Force JSON → SQLite migration |

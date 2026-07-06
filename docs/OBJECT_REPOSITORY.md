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

Every successful `find_element`, `click_element`, or `smart_find` (with `remember=true`, default) saves:
- Full detectable properties
- Identification tiers (mandatory / assistive / smart / ordinal)
- Last resolution (backend, bbox)
- Optional snapshots when `AWDUI_SNAPSHOT=1`

Objects are keyed by stable `repo_path` (e.g. `Calculadora/num6Button`).

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

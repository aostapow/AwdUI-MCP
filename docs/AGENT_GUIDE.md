# AwdUI Agent Guide

Quick reference for Claude and other AI agents using AwdUI tools.

## Tool catalog (read first)

**Full per-tool reference:** [MCP_TOOLS_REFERENCE.md](MCP_TOOLS_REFERENCE.md) — what each of the ~66 MCP tools does, parameters, examples, and when to use it.  
Keep it updated when adding/changing/removing tools (see `.cursor/rules/awdui-tools-catalog.mdc`).

## Tool Selection Flow

Use this priority order when interacting with a GUI:

1. **`find_element` / `click_element`** — First choice. Uses the accessibility tree. Fast, precise, works on most standard widgets.
2. **`smart_find`** — When unsure. Tries accessibility first, falls back to OCR automatically.
3. **`find_text` / `click_text`** — OCR fallback. Use when accessibility can't see the element (custom widgets, canvas content). `click_text` auto-retries nearby offsets if the center click has no effect.
4. **`screenshot(region=...)` + visual inspection** — Last resort. Crop a region, read coordinates visually, click by position.

## Starting on a New App

1. Call `detect_framework` to understand what toolkit the app uses
2. Call `get_automation_profile` for preferred/blocked tools and app-specific notes (matrix in `detection/framework_capabilities.py`)
3. Before interacting with an **unfamiliar control**, call `discover_control_interaction(automation_id=...)` — do not guess calendar vs type vs combo
4. Call `list_elements` to see what's accessible
5. If few elements found, try `list_elements(role="Button")` to search deeper
6. Check framework hints for tips (e.g., Electron may need accessibility flag)
7. For each control: match **role** + **patterns** to the [control catalog](../.cursor/skills/awdui-flow-exploration/patterns/control-catalog.md) (ComboBox → list items first; Table → grid row tools; Button → invoke)

## Focus Management

**Set a target window early.** Call `set_target_window("Browser")` (or whatever app you're automating) at the start of a session. This auto-focuses the target before every input action, preventing the terminal from stealing focus between tool calls.

**Scope enforcement:** With a target set, clicks and UIA actions (`set_element_value`, `invoke_element`, `click_element`, pattern tools) are **blocked** if the element or coordinates belong to another app (e.g. browser address bar behind the form). Modal dialogs (`window_title="Buscar"`) are resolved as same-process children of the target.

Clear it when switching apps or when done: `set_target_window("")`.

## Screenshots on action tools

Action tools accept an optional `capture` parameter. **Default is `false`** (fast, text-only response).

| Tool | `capture` default | When to set `capture=true` |
|------|-------------------|----------------------------|
| `click`, `drag`, `scroll` | `false` | Debug a single coordinate action |
| `click_element`, `click_text` | `false` | Verify one UI click visually |
| `batch_actions` | `true` | Set `capture=false` for max speed |
| `invoke_element` | n/a | Never screenshots — prefer for UWP/button chains |
| `screenshot` | n/a | Explicit capture when you need an image |

**Fast execution pattern:** map objects once (`list_elements`), then chain `invoke_element` or `click_element(capture=false)`. Call `screenshot()` once at the end to verify.

**Avoid:** calling `screenshot()` or `capture=true` after every step — each image costs seconds.

## Auto-update

- MCP entry point: `scripts/launcher.py` (not `server.py` directly)
- Tool `get_server_info` — version, `updateAvailable`, `lastAppliedVersion`
- Manual update: `python scripts/update.py`
- See [AGENTS_AUTOUPDATE.md](AGENTS_AUTOUPDATE.md)

## Performance (fast mode — default)

AwdUI runs in **fast mode** by default since vNext:

| What | Fast (default) | Slow (`AWDUI_VERIFY=1`) |
|------|----------------|---------------------------|
| `click` / `scroll` | No before/after screenshot diff | Full pixel comparison |
| `ensure_focus` | Cached ~3s if target already foreground | Refocus every action |
| `find_element` / `smart_find` | First backend match, no extra tree walk | Quality-gate tree scan |
| `detection_health` | Availability only | Counts elements per backend |
| `smart_find` snapshots | Off unless `remember_snapshot=true` | `AWDUI_SNAPSHOT=1` saves images |

Environment variables:

- `AWDUI_VERIFY=1` — restore visual verification on click/scroll
- `AWDUI_SNAPSHOT=1` — save crop/template images on every `smart_find` remember
- `AWDUI_HEALTH_FULL=1` — full element counts in `detection_health`
- `AWDUI_FOCUS_TTL=3` — seconds to skip redundant focus (default 3)

**Fast Paint / WinForms flow:** `set_target_window` once → `invoke_element` / `click_element(capture=false)` / `batch_actions(capture=false)` → one `screenshot()` at the end.

### Combos, patterns y lookup dialogs

- **`get_control_state`** — leer Toggle, Range, Scroll %, Expand antes de actuar.
- **`invoke_pattern`** — Toggle, ExpandCollapse, RangeValue, SelectionItem, VirtualizedItem.
- **`scroll_element`** — scroll UIA en contenedor (grillas virtualizadas).
- **`select_grid_cell`** — fila de grilla por índice numérico.
- **`list_control_items`** — paginated items for a known `automation_id` (combo, list, grid). No full-window tree walk.
- **`select_control_item`** — pick by substring; use `double_click=true` for WinForms lookup grids.
- **`select_lookup_row`** — shortcut for modal search grids (`double_click=true` by default).
- **`list_elements(max_depth=0)`** — default is full tree; use `role="ComboBox"` filter for fast combo discovery.
- **`observe_ui_tool`** — capped at depth 8 / 80 elements; use only for initial exploration, not per-step execution.
- **MDI child forms:** if `window_title` partial fails, set `set_target_window` to the parent app — OCR/UIA resolve same-process child windows automatically.

## Coordinate System

Screenshots are downscaled to 1280px max width for transport. All tool coordinates use **screen coordinates** (physical pixels), not screenshot pixels.

- **Never estimate coordinates from the screenshot image** — they will be wrong
- Use `find_text` or `find_element` to get real screen coordinates for anything you see
- Use `screenshot(annotate=True)` to see a grid with screen-coordinate labels

## Browser Web Content

The accessibility tree only covers browser chrome (tabs, address bar, toolbar). Web page content is invisible to `find_element` / `click_element` / `list_elements`.

For web forms: **Tab between fields, never click contenteditable/textarea directly.** They often ignore mouse clicks.
- OCR click for buttons/links: `find_text("Submit")` → `click` at those coordinates
- `Tab` / `Shift+Tab` to move between form fields
- `clipboard(action="write", text="...")` then `send_keys("ctrl+v")` for text entry
- `scroll(x, y, "down", pages=1)` for page-at-a-time scrolling (uses PageDown/PageUp keys internally — DPI-independent)

## Prefer Keyboard Shortcuts Over Mouse

**Use `send_keys` with keyboard shortcuts whenever practical.** Shortcuts are faster, more reliable, and don't depend on element coordinates or screen layout:

- **New tab**: `send_keys("ctrl+t")` instead of clicking the + button
- **Close tab**: `send_keys("ctrl+w")` instead of clicking the X
- **Navigate back**: `send_keys("alt+left")` instead of finding the back button
- **Address bar**: `send_keys("ctrl+l")` or `send_keys("f6")` instead of clicking the URL bar
- **Save**: `send_keys("ctrl+s")` instead of File > Save
- **Select all + copy**: `send_keys("ctrl+a")` then `send_keys("ctrl+c")` instead of drag-selecting
- **Tab between form fields**: `send_keys("tab")` instead of clicking each field
- **Submit forms**: `send_keys("enter")` instead of clicking Submit
- **Switch apps**: `send_keys("alt+tab")` as an alternative to `focus_window`

Reserve mouse clicks for elements that have no keyboard shortcut (custom buttons, specific list items, canvas content).

## Common Patterns

### Navigate and Verify
```
click_element(name="Settings") → screenshot(region) to verify
```

### Data Entry
```
batch_actions([
    {"action": "click", "x": 100, "y": 200},
    {"action": "type", "text": "hello@example.com"},
    {"action": "keys", "keys": "tab"},
    {"action": "type", "text": "password123"},
    {"action": "keys", "keys": "enter"}
])
```

### Confirm Focus Before Typing
```
get_focused_element → verify it's the right field → type_text
```

### Find All Form Fields
```
list_elements(role="Spinner")   → all numeric inputs
list_elements(role="Edit")      → all text fields
list_elements(role="ComboBox")  → all dropdowns
```

## When Done

**Call `focus_window(title="Claude")` as your last action** so the user sees you've finished. Without this, the user has no signal that you're done — the target app stays in the foreground and they'll be waiting.

## Tips

- Use `batch_actions` for click-type-enter sequences to reduce round-trips
- Use `screenshot(annotate=True)` to see element outlines and mouse position
- Multi-word OCR queries work: `find_text("Save As PDF")` matches adjacent words
- OCR automatically retries with image inversion for dark backgrounds
- The accessibility tree is DPI-aware — coordinates are always screen-absolute


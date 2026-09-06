# Changelog

## 0.4.0

WinApp-style session model and unified tool surface (111 tools).

- **Session / attach**: `attach_to_app`, `attach_to_pid`, `list_apps`, `close_app`, `app_id` session model, `release_keyboard`
- **Discovery**: `find_elements`, `find_elements_fuzzy`, `get_snapshot_hwnd`, `get_tree_hash`, `get_element_bounds`, fuzzy matching layer
- **Actions**: `click_element_hwnd`, `double_click_element`, `right_click_element`, `drag_element`, `expand_collapse_element`, `select_option`, `set_value_hwnd`, `type_into_element`, `press_key`, `press_key_combo`
- **Screenshots**: `take_screenshot_optimized`, `annotate_screenshot`, `compare_screenshot_files`; improved `screenshot` / `visual_diff`
- **Consolidation**: WinApp parity folded into core modules (`ui_automation`, `session_tools`, `windows`); removed `winapp_parity.py` shim
- **Docs**: `MCP_TOOLS_REFERENCE.md` expanded with per-module index (111 tools); catalog sync/audit scripts
- **Tests**: `test_extended_ui`, updated tools reference matrix, framework capabilities coverage

## 0.3.0

Major expansion of UIA tooling, detection scope, and agentic improvement cycle.

- **Tools (87)**: `ascii_ui_view`, `wait_for_element` / `wait_for_condition` / `wait_for_input_idle`, `element_exists`, session/cache tools, `fill_form` / `get_all_values`, `list_control_items` / `select_control_item`, `get_grid_item` / `read_table`, `expand_element`, `start_event_monitor` / `get_event_log`, and more — see `docs/MCP_TOOLS_REFERENCE.md`
- **Detection**: window/HWND scope, element dedupe, spatial clustering, UIA control map, tree depth/caching, WinForms combo helpers, post-action verify target
- **Event sidecar**: new `awdui-event-sidecar` for UIA structure/property change events
- **Calculator lab**: integration harness, coverage docs, MCP improvement cycle (skills, rules, hooks)
- **Repo / Spy**: target-window scoping for `list_elements` and `spy_tree`, expand-element fallbacks, filter scope for UWP screen coords
- **Tests**: broad new unit/integration coverage; tools reference validation script
- **Cursor**: agent skills (flow exploration, AST, calculator harness), improvement advisor backlog in `_MCP_IMPROVEMENT/`

## 0.2.1

Fix repo element image crops and align highlight with UIA screen coordinates.

- **Element bbox**: `element_screen_bbox()` prefers UIA `list_elements` rectangles; spy offset conversion no longer mis-crops UWP controls (e.g. Calculator `num6Button`)
- **Snapshots**: `object_snapshot` captures via screen crop only, using the same bbox path as highlight
- **Coordinates**: `element_coords.to_screen_coords()` handles logical/physical window-relative vs screen space and DPI edge cases
- **Repo lookup**: auto-lookup, consolidation, and `app_identity` for resolving objects across windows
- **Repo Studio**: live polling refresh in the web UI; `refresh_repo_window.py` batch script for re-capturing all objects in a window
- **Tests**: expanded coverage for element_coords, element_snapshot, repo_store, repo_lookup, repo_consolidate

## 0.2.0

Major update to object repository, detection, and Windows platform layer.

- **Object repository**: SQLite-backed store (`repo_store`) with legacy JSON migration, auto-remember (`auto_repo`), element snapshots, and coordinate helpers
- **Repo Studio**: FastAPI backend (`repo-api`) and React web UI (`repo-web`) for browsing and editing repository objects
- **Screenshot tool**: window-scoped capture, DPI-aware regions, post-action capture on clicks, improved `scope` handling
- **Windows platform**: consolidated `list_windows_native` / `focus_window_native` in `win32_backend`; UIA sidecar improvements
- **Detection**: layered detector refinements, richer `object_snapshot`, shared `params` for window title resolution
- **Spy sidecar**: highlight overlay and bridge improvements
- **Scripts**: MCP restart, venv setup, JAB offline setup, repo studio launcher, legacy profile migration
- **Tests**: new coverage for auto_repo, element_coords, repo_store, spy_bridge, params/windows; updated tool counts (58 tools)
- **Cursor rules**: workspace rules for MCP restart and post-change testing

## 0.1.0

Initial release of **AwdUI-MCP** — advanced desktop UI automation for Claude Code and MCP clients.

- Screen capture, mouse/keyboard input, and accessibility-tree targeting (UIA / AX)
- OCR and visual fallbacks via `smart_find`
- Framework detection, object repository, Spy sidecar, discovery protocol
- 58 MCP tools for Windows and macOS
- Auto-update from GitHub Releases via `scripts/launcher.py`
- Claude Code plugin with `/awdui` command and `awdui-mcp` skill

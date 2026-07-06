# Changelog

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

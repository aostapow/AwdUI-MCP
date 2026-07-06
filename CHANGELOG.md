# Changelog

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

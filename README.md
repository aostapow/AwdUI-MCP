# AwdUI-MCP

[![GitHub release](https://img.shields.io/github/v/release/aostapow/AwdUI-MCP?style=flat-square)](https://github.com/aostapow/AwdUI-MCP/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-lightgrey?style=flat-square)]()
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-plugin-blueviolet?style=flat-square)](https://docs.anthropic.com/en/docs/claude-code)
[![MCP](https://img.shields.io/badge/MCP-server-orange?style=flat-square)](https://modelcontextprotocol.io)
[![Tools](https://img.shields.io/badge/tools-58-green?style=flat-square)]()

Advanced desktop UI automation for Claude. A Claude Code plugin and MCP server that lets Claude see your screen and interact with applications on your desktop.

> **Alpha software.** AwdUI works and is genuinely useful, but complex multi-step workflows may take several retries. Set your expectations accordingly.

## Why AwdUI?

Claude Code is powerful, but it cannot see your screen or interact with anything outside the terminal. AwdUI gives Claude eyes and hands for desktop apps — navigate UIs, fill forms, click dialogs, and verify results visually.

**Core capabilities:**

- **Accessibility-first targeting** — Windows uses a multi-backend detection stack (UIA, MSAA, Win32 HWND, Java Access Bridge, optional FlaUI sidecar). macOS uses AXUIElement (Accessibility API) for core find/list/click flows.
- **Object repository** — Successful finds are remembered in `~/.awdui-mcp/repository.db`. `find_element`, `click_element`, and `smart_find` try the repo **first** (by `automation_id`, name, or digit → `numNButton`) before live UI discovery.
- **Property-based actions** — Repository objects resolve and click via **UIA properties** (`automation_id`, `InvokePattern`), not cached screen coordinates.
- **Framework-aware hints** — Detects toolkit by process/bundle (Qt, WPF, Electron, Cocoa, etc.) and returns actionable guidance.
- **58 MCP tools** — Screenshots, input, windows, OCR, discovery, object repository, Spy sidecar (Windows), batch actions, watchers, and more.

## Platform support

Windows is the primary, most complete target. macOS is supported for common automation flows but several advanced tools are Windows-only or still stubbed.

| Area | Windows | macOS |
|------|---------|-------|
| Screenshots, input, clipboard | Full | Full (Vision OCR; `cmd`/`option` modifiers for shortcuts) |
| Window list / focus / launch | Win32 APIs | AppleScript + Quartz |
| `find_element`, `list_elements`, `click_element` | UIA orchestrator + repo auto-lookup + DPI normalization | AXUIElement tree (`name` / `role` only) |
| `click_element` fallback | Repo → native UIA/spy (no OCR) | AX only |
| `smart_find` | Full cascade (repo → native → OCR → visual → agentic) | AX → OCR |
| `get_focused_element` | UIA | AX |
| `invoke_element`, `set_element_value` | UIA patterns | Not available |
| `element_at_point`, `get_element_properties` | Multi-backend | Not implemented yet |
| Object repository (`repo_find`, `repo_action`) | Full | `repo_list` / hints work; resolve & actions are Windows-only |
| Spy sidecar (`spy_inspect`, `spy_tree`, highlights) | Windows `.exe` sidecar | Requires sidecar build (Windows only) |
| Detection orchestrator (UIA/MSAA/JAB/FlaUI) | Yes | No — single AX backend |
| `configure_uac`, console input routing | Win32 console APIs | N/A (pyautogui passthrough) |
| Virtual desktops | Create/switch/close | Switch Spaces only (no programmatic create/close) |
| Framework detection | EXE/class analysis | Bundle ID patterns (Cocoa, Qt, Electron, Java, …) |

**macOS requirements:** grant **Accessibility** and **Screen Recording** to the terminal or IDE running the MCP server (System Settings → Privacy & Security). AwdUI checks these at startup and logs missing permissions.

**Requirements:** Python 3.10+, Windows 10/11 or macOS 12+.

## Quick Start

### Install (Claude Code plugin)

```bash
claude plugin marketplace add aostapow/AwdUI-MCP
claude plugin install awdui-mcp
```

Restart Claude Code after installing. Python dependencies are installed automatically on first run (PyObjC on macOS, pywinauto/pywin32 stack on Windows).

To update:

```bash
claude plugin marketplace update awdui-mcp
claude plugin update awdui-mcp
```

### MCP client (Cursor, etc.)

Point your MCP config at the launcher (not `server.py` directly):

```json
{
  "mcpServers": {
    "awdui": {
      "command": "python",
      "args": ["C:\\path\\to\\AwdUI-MCP\\scripts\\launcher.py"]
    }
  }
}
```

See [docs/AGENTS_AUTOUPDATE.md](docs/AGENTS_AUTOUPDATE.md) for auto-update and `.env` options.

### Try It

```
"Open Settings and tell me my display resolution"
"Launch Calculator and compute 15 × 7 using the buttons"
"Screenshot the foreground window and describe what you see"
```

Use `/awdui` to start a guided automation session.

## Tools (overview)

| Category | Examples | Notes |
|----------|----------|-------|
| Vision | `screenshot`, `wait_for_change`, `get_screen_size` | Cross-platform |
| Input | `click`, `type_text`, `scroll`, `drag`, `batch_actions` | macOS uses AppleScript for key combos |
| Accessibility | `find_element`, `click_element`, `smart_find`, `list_elements` | See platform table above |
| OCR | `find_text`, `click_text` | Vision on macOS; RapidOCR + Windows OCR fallback on Windows |
| Windows | `list_windows`, `focus_window`, `launch_app`, `set_target_window` | Cross-platform (name is historical) |
| Repository | `repo_find`, `repo_list`, `repo_action`, `repo_capture` | Resolve/actions: Windows-only |
| Discovery | `observe_ui_tool`, `discover_target_tool`, `find_by_template_tool` | Tree detail richest on Windows |
| Spy | `spy_inspect`, `spy_tree`, `highlight_element` | Windows sidecar (`.exe`) |
| Utility | `check_version`, `get_server_info`, `configure_uac` | UAC is Windows-only |

Full reference: [docs/AGENT_GUIDE.md](docs/AGENT_GUIDE.md)

## How targeting works

### Which tool when?

| Situation | Tool |
|-----------|------|
| Control already in repo, or standard app (Calculator, dialogs) | `click_element` or `repo_action("App/window/btnOk", "Click")` |
| First time / unsure locator / need highlight | `smart_find(name=..., highlight=true)` — auto-saves to repo on success |
| `click_element` fails, tree sparse, custom-painted UI | `smart_find` (adds OCR + visual layers) |
| Menus/tabs hidden, need to open before finding children | `plan_probes_tool` → `apply_probe_tool` → `discover_target_tool` |
| Text visible but no accessibility node | `find_text` / `click_text` |
| Browser **page** content (not chrome) | Tab, clipboard, `find_text` — not `find_element` |

Exploration workflow for multi-step flows: [.cursor/skills/awdui-flow-exploration/SKILL.md](.cursor/skills/awdui-flow-exploration/SKILL.md)

### Layered cascade (`smart_find`)

**Windows** — full layered cascade:

```
smart_find("Submit")
    → Object repository (auto-match by name / automation_id)
    → Accessibility tree (UIA → MSAA → Win32 → JAB → FlaUI)
    → OCR text recognition
    → Visual / template matching
    → Agentic context (optional, agentic=true)
```

**`click_element` / `find_element`** use a **shorter** path: repository first, then native accessibility only (no OCR/visual). Use `smart_find` when that is not enough.

**macOS** — simplified cascade:

```
smart_find("Submit")
    → AXUIElement tree (find by name / role)
    → OCR (Vision framework)
```

On both platforms, coordinates returned by `find_element` on Windows are normalized to physical screen space via `to_screen_coords`. On macOS, click targeting applies DPI adjustment at click time; list/find results use AX coordinates directly.

Prefer `set_target_window("AppName")` early in a session so input and screenshots stay scoped to the right application.

### Object repository

- Stored in `~/.awdui-mcp/repository.db` (SQLite). Browse/edit with **Repo Studio**: `scripts/start-repo-studio.ps1`
- Every successful `smart_find` / `click_element` / `find_element` with `remember=true` (default) upserts identification properties for next time
- Resolution uses stored **properties** (`automation_id`, name, role) and `InvokePattern` — not coordinate replay

Details: [docs/OBJECT_REPOSITORY.md](docs/OBJECT_REPOSITORY.md)

## Documentation

- [Agent Guide](docs/AGENT_GUIDE.md) — tool selection, performance, browser/content caveats
- [Object Repository](docs/OBJECT_REPOSITORY.md) — auto-lookup, `repo_action`, Repo Studio
- [Discovery Protocol](docs/DISCOVERY_PROTOCOL.md) — probes and `discover_target_tool`
- [Framework Support](docs/FRAMEWORK_SUPPORT.md) (Windows-focused matrix)
- [Detection Architecture](docs/DETECTION_ARCHITECTURE.md)
- [Auto-update for agents](docs/AGENTS_AUTOUPDATE.md)

## License

MIT

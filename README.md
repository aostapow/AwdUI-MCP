# AwdUI-MCP

[![GitHub release](https://img.shields.io/github/v/release/aostapow/AwdUI-MCP?style=flat-square)](https://github.com/aostapow/AwdUI-MCP/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-lightgrey?style=flat-square)]()
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-plugin-blueviolet?style=flat-square)](https://docs.anthropic.com/en/docs/claude-code)
[![MCP](https://img.shields.io/badge/MCP-server-orange?style=flat-square)](https://modelcontextprotocol.io)
[![Tools](https://img.shields.io/badge/tools-58-green?style=flat-square)]()

Advanced desktop UI automation for Claude. A Claude Code plugin and MCP server that lets Claude see your screen and interact with any application on your desktop.

> **Alpha software.** AwdUI works and is genuinely useful, but complex multi-step workflows may take several retries. Set your expectations accordingly.

## Why AwdUI?

Claude Code is powerful, but it cannot see your screen or interact with anything outside the terminal. AwdUI gives Claude eyes and hands for desktop apps — navigate UIs, fill forms, click dialogs, and verify results visually.

**Core capabilities:**

- **Accessibility-first** — UIA (Windows) and AXUIElement (macOS) for DPI-aware element targeting
- **Automatic fallbacks** — OCR and visual analysis when the accessibility tree is incomplete
- **Framework-aware** — Detects Qt, WPF, Electron, WinForms, and more with actionable hints
- **58 MCP tools** — Screenshots, input, windows, discovery, repository, Spy sidecar, batch actions

## Quick Start

### Install (Claude Code plugin)

```bash
claude plugin marketplace add aostapow/AwdUI-MCP
claude plugin install awdui-mcp
```

Restart Claude Code after installing. Python dependencies are installed automatically on first run.

To update:

```bash
claude plugin marketplace update awdui-mcp
claude plugin update awdui-mcp
```

**Requirements:** Python 3.10+, Windows 10/11 or macOS 12+.

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

| Category | Examples |
|----------|----------|
| Vision | `screenshot`, `wait_for_change`, `get_screen_size` |
| Input | `click`, `type_text`, `scroll`, `drag`, `batch_actions` |
| Accessibility | `find_element`, `click_element`, `smart_find`, `list_elements` |
| OCR | `find_text`, `click_text` |
| Windows | `list_windows`, `focus_window`, `launch_app`, `set_target_window` |
| Discovery | `observe_ui_tool`, `discover_target_tool`, `find_by_template_tool` |
| Utility | `check_version`, `get_server_info`, `configure_uac` |

Full reference: [docs/AGENT_GUIDE.md](docs/AGENT_GUIDE.md)

## How targeting works

```
smart_find("Submit")
    → Accessibility tree (UIA / AX)
    → OCR text recognition
    → Framework hints + visual fallback
```

## Documentation

- [Agent Guide](docs/AGENT_GUIDE.md)
- [Framework Support](docs/FRAMEWORK_SUPPORT.md)
- [Auto-update for agents](docs/AGENTS_AUTOUPDATE.md)

## License

MIT

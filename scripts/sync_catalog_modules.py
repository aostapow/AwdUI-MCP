#!/usr/bin/env python3
"""Sync module index and **Módulo:** fields in MCP_TOOLS_REFERENCE.md from code."""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO / "mcp-servers" / "awdui-server" / "tools"
REFERENCE = REPO / "docs" / "MCP_TOOLS_REFERENCE.md"

MODULE_INDEX_START = "<!-- MODULE_INDEX:START -->"
MODULE_INDEX_END = "<!-- MODULE_INDEX:END -->"
MODULE_PATH = "mcp-servers/awdui-server/tools/{module}.py"


def discover_tools() -> dict[str, dict]:
    found: dict[str, dict] = {}
    for path in sorted(TOOLS_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            is_tool = any(
                (isinstance(d, ast.Call) and getattr(d.func, "attr", "") == "tool")
                or (isinstance(d, ast.Attribute) and d.attr == "tool")
                for d in node.decorator_list
            )
            if not is_tool:
                continue
            found[node.name] = {"module": path.stem, "line": node.lineno}
    return found


def build_module_index_table(tools: dict[str, dict]) -> str:
    lines = [
        MODULE_INDEX_START,
        "",
        "### Índice alfabético por módulo",
        "",
        "Ruta base: `mcp-servers/awdui-server/tools/`. Generado desde `@server.tool()` en código.",
        "",
        "| Tool | Módulo | Archivo |",
        "|------|--------|---------|",
    ]
    for name in sorted(tools):
        mod = tools[name]["module"]
        rel = MODULE_PATH.format(module=mod)
        lines.append(f"| `{name}` | `{mod}` | `{rel}` |")
    lines.extend(["", MODULE_INDEX_END])
    return "\n".join(lines)


def inject_module_fields(text: str, tools: dict[str, dict]) -> str:
    for name in sorted(tools, key=len, reverse=True):
        mod = tools[name]["module"]
        rel = MODULE_PATH.format(module=mod)
        header = f"### `{name}`"
        idx = text.find(header)
        if idx == -1:
            continue
        after = text[idx + len(header) : idx + len(header) + 80]
        if "**Módulo:**" in after.split("\n\n")[0] + (after.split("\n\n")[1] if "\n\n" in after else ""):
            # already has module in first lines after header
            block = text[idx : idx + 200]
            if re.search(rf"### `{name}`\s*\n\n\*\*Módulo:\*\*", block):
                # update existing module line
                text = re.sub(
                    rf"(### `{name}`\s*\n\n)\*\*Módulo:\*\*[^\n]*\n",
                    rf"\1**Módulo:** `{mod}` (`{rel}`)\n",
                    text,
                    count=1,
                )
                continue
        text = text.replace(
            f"{header}\n\n",
            f"{header}\n\n**Módulo:** `{mod}` (`{rel}`)\n\n",
            1,
        )
    return text


def replace_or_insert_index(text: str, table: str) -> str:
    if MODULE_INDEX_START in text and MODULE_INDEX_END in text:
        start = text.index(MODULE_INDEX_START)
        end = text.index(MODULE_INDEX_END) + len(MODULE_INDEX_END)
        return text[:start] + table + text[end:]

    # Replace legacy alphabetical comma list
    legacy = re.compile(
        r"\*\*Lista alfabética \(\d+\):\*\*\s*\n`[^`]+(?:`, `[^`]+)*`\.?\s*\n",
        re.M,
    )
    if legacy.search(text):
        return legacy.sub(table + "\n\n", text, count=1)

    # Fallback: insert before Convenciones comunes
    anchor = "## Convenciones comunes"
    return text.replace(anchor, table + "\n\n" + anchor, 1)


def main() -> int:
    tools = discover_tools()
    if not tools:
        print("No tools discovered", file=sys.stderr)
        return 1

    text = REFERENCE.read_text(encoding="utf-8")
    table = build_module_index_table(tools)
    text = replace_or_insert_index(text, table)
    text = inject_module_fields(text, tools)
    REFERENCE.write_text(text, encoding="utf-8")
    print(f"sync_catalog_modules: {len(tools)} tools, {len({t['module'] for t in tools.values()})} modules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

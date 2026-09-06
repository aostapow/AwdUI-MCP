#!/usr/bin/env python3
"""Compare MCP tool signatures in code vs **Parámetros clave** in the catalog.

Exit 0 if no missing required params in docs; exit 1 with report otherwise.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO / "mcp-servers" / "awdui-server" / "tools"
REFERENCE = REPO / "docs" / "MCP_TOOLS_REFERENCE.md"

# Params documented in convenciones — not repeated per tool
GLOBAL_PARAMS = {"window_title", "title", "window_handle", "app_id", "capture", "capture_full", "role"}

# Aliases / grouped names in docs
ALIASES = {
    "control_type": "role",
    "hwnd": "window_handle",
    "fields": "fields_json",
    "fields_json": "fields",
    "source_control_type": "role",
    "target_control_type": "role",
    "option_text": "value",
    "keys": "key",
    "image_path1": "image_path",
    "image_path2": "image_path",
}


def discover_signatures() -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for path in sorted(TOOLS_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not any(
                (isinstance(d, ast.Call) and getattr(d.func, "attr", "") == "tool")
                or (isinstance(d, ast.Attribute) and d.attr == "tool")
                for d in node.decorator_list
            ):
                continue
            params = {a.arg for a in node.args.args if a.arg not in ("self", "cls")}
            out[node.name] = params
    return out


def doc_params(tool: str, text: str) -> set[str]:
    m = re.search(
        rf"### `{tool}`\s*\n(?:.*?\n)*?\*\*Parámetros clave:\*\* ([^\n]+)",
        text,
        re.M,
    )
    if not m:
        return set()
    line = m.group(1)
    if line.strip() in ("—", "— (sin parámetros).", "— (sin parámetros)"):
        return set()
    names = set(re.findall(r"`([a-z][a-z0-9_]*)`", line))
    expanded: set[str] = set()
    for n in names:
        expanded.add(ALIASES.get(n, n))
        if n.startswith("source_"):
            expanded.add(n.replace("source_", ""))
        if n.startswith("target_"):
            expanded.add(n.replace("target_", ""))
    return expanded


def main() -> int:
    sigs = discover_signatures()
    text = REFERENCE.read_text(encoding="utf-8")
    issues: list[str] = []

    for tool, params in sorted(sigs.items()):
        if not params:
            continue
        documented = doc_params(tool, text)
        # required = no default in AST is hard; flag params not in doc unless global
        missing = []
        for p in sorted(params):
            canon = ALIASES.get(p, p)
            if canon in GLOBAL_PARAMS:
                continue
            if p in documented or canon in documented:
                continue
            if p.startswith("verify_") and "verify_" in " ".join(documented):
                continue
            if p in {"capture", "capture_full"}:
                continue
            missing.append(p)
        if missing:
            issues.append(f"{tool}: undocumented in Parámetros clave → {', '.join(missing)}")

    if issues:
        print("CATALOG PARAM GAPS\n", file=sys.stderr)
        for line in issues:
            print(line, file=sys.stderr)
        print(f"\n{len(issues)} tools with possible gaps", file=sys.stderr)
        return 1

    print(f"OK — param spot-check passed for {len(sigs)} tools")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

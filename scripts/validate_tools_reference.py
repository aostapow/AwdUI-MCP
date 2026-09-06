#!/usr/bin/env python3
"""Validate docs/MCP_TOOLS_REFERENCE.md against registered MCP tools.

Checks:
  1. Every @server.tool() appears in the quick-index section.
  2. Every tool has a dedicated ### `tool_name` section (no grouped headers).
  3. Each dedicated section includes minimum template fields (+ **Módulo:**).
  4. Module index table and **Módulo:** fields match code.

Usage:
    python scripts/validate_tools_reference.py
    python scripts/validate_tools_reference.py --list
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "mcp-servers" / "awdui-server" / "tools"
REFERENCE = REPO_ROOT / "docs" / "MCP_TOOLS_REFERENCE.md"

_REQUIRED_MARKERS = (
    "**Qué hace:**",
    "**Cuándo",
    "**Parámetros",
    "**Ejemplo:**",
)


def _discover_tools() -> dict[str, dict]:
    """Return {tool_name: {module, doc, line}} from register() blocks."""
    found: dict[str, dict] = {}
    for path in sorted(TOOLS_DIR.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            raise SystemExit(f"Syntax error in {path}: {exc}") from exc
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
            doc = ast.get_docstring(node) or ""
            first_line = doc.strip().split("\n")[0] if doc.strip() else ""
            found[node.name] = {
                "module": path.stem,
                "doc": first_line,
                "line": node.lineno,
            }
    return found


def _tools_in_reference_index(text: str) -> set[str]:
    """Extract tool names from markdown backticks in the quick-index block."""
    in_index = False
    names: set[str] = set()
    for line in text.splitlines():
        if line.strip().startswith("## Índice rápido"):
            in_index = True
            continue
        if in_index and (
            "<!-- MODULE_INDEX:START -->" in line
            or (line.startswith("## ") and "Índice" not in line)
        ):
            break
        if in_index:
            names.update(re.findall(r"`([a-z][a-z0-9_]*)`", line))
    return names


def _dedicated_sections(text: str) -> dict[str, str]:
    """Map tool_name -> section body for ### `tool_name` headers (single tool only)."""
    sections: dict[str, str] = {}
    pattern = re.compile(r"^### `([^`]+)`\s*$", re.M)
    matches = list(pattern.finditer(text))
    for i, match in enumerate(matches):
        header = match.group(1).strip()
        if "/" in header:
            continue
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[header] = text[start:end]
    return sections


def _module_index_from_doc(text: str) -> dict[str, str]:
    """Parse MODULE_INDEX table: tool -> module stem."""
    if "<!-- MODULE_INDEX:START -->" not in text:
        return {}
    start = text.index("<!-- MODULE_INDEX:START -->")
    end = text.index("<!-- MODULE_INDEX:END -->")
    block = text[start:end]
    out: dict[str, str] = {}
    for line in block.splitlines():
        if not line.startswith("| `"):
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) >= 2:
            tool = parts[0].strip("`")
            mod = parts[1].strip("`")
            out[tool] = mod
    return out


def _module_in_sections(text: str) -> dict[str, str]:
    """Parse **Módulo:** lines under ### headers."""
    out: dict[str, str] = {}
    pattern = re.compile(
        r"^### `([^`]+)`\s*\n\n\*\*Módulo:\*\* `([^`]+)`",
        re.M,
    )
    for tool, mod in pattern.findall(text):
        out[tool] = mod
    return out


def _section_issues(body: str) -> list[str]:
    issues: list[str] = []
    for marker in _REQUIRED_MARKERS:
        if marker not in body:
            issues.append(f"missing {marker}")
    if "**Evitar:**" not in body and "**Evitar**" not in body:
        issues.append("missing **Evitar:**")
    if "**Relacionadas:**" not in body:
        issues.append("missing **Relacionadas:**")
    if "**Módulo:**" not in body:
        issues.append("missing **Módulo:**")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true", help="List discovered tools")
    args = parser.parse_args()

    discovered = _discover_tools()
    if args.list:
        for name in sorted(discovered):
            info = discovered[name]
            doc = info["doc"].encode("ascii", "replace").decode("ascii")
            print(f"{name:30}  {info['module']:20}  {doc[:60]}")
        print(f"\nTotal: {len(discovered)} tools")
        return 0

    if not REFERENCE.exists():
        print(f"Missing reference: {REFERENCE}", file=sys.stderr)
        return 1

    ref_text = REFERENCE.read_text(encoding="utf-8")
    documented_index = _tools_in_reference_index(ref_text)
    dedicated = _dedicated_sections(ref_text)
    code_names = set(discovered)

    errors: list[str] = []

    missing_in_doc = sorted(code_names - documented_index)
    if missing_in_doc:
        errors.append(
            "Tools in code but missing from quick index:\n  " + ", ".join(missing_in_doc)
        )

    extra_in_doc = sorted(documented_index - code_names)
    if extra_in_doc:
        errors.append(
            "Tools in index but not registered in code:\n  " + ", ".join(extra_in_doc)
        )

    missing_sections = sorted(code_names - set(dedicated))
    if missing_sections:
        errors.append(
            "Tools without dedicated ### `tool` section (no grouped headers):\n  "
            + ", ".join(missing_sections)
        )

    incomplete: list[str] = []
    for name in sorted(code_names):
        body = dedicated.get(name, "")
        issues = _section_issues(body)
        if issues:
            incomplete.append(f"{name}: {', '.join(issues)}")
    if incomplete:
        errors.append(
            "Incomplete tool sections (template fields):\n  " + "\n  ".join(incomplete[:20])
        )
        if len(incomplete) > 20:
            errors.append(f"  ... and {len(incomplete) - 20} more")

    module_index = _module_index_from_doc(ref_text)
    module_sections = _module_in_sections(ref_text)
    for name in sorted(code_names):
        expected = discovered[name]["module"]
        if module_index.get(name) != expected:
            errors.append(
                f"Module index mismatch for {name}: "
                f"doc={module_index.get(name)!r} code={expected!r}"
            )
        if module_sections.get(name) != expected:
            errors.append(
                f"Section **Módulo:** mismatch for {name}: "
                f"doc={module_sections.get(name)!r} code={expected!r}"
            )

    grouped = [
        m.group(1)
        for m in re.finditer(r"^### `([^`]+)`\s*$", ref_text, re.M)
        if "/" in m.group(1)
    ]
    if grouped:
        errors.append(
            "Grouped section headers are not allowed (split into one ### per tool):\n  "
            + ", ".join(grouped)
        )

    if errors:
        print("TOOLS REFERENCE OUT OF DATE\n", file=sys.stderr)
        for err in errors:
            print(err, file=sys.stderr)
        print(
            "\nFix: update docs/MCP_TOOLS_REFERENCE.md "
            "(see .cursor/rules/awdui-tools-catalog.mdc)",
            file=sys.stderr,
        )
        return 1

    print(f"OK — {len(code_names)} tools documented with dedicated sections")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

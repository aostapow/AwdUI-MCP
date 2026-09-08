#!/usr/bin/env python3
"""Validate runs/{run_id}/flows.json structure (lab flow tree)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

VALID_KINDS = frozenset({"entry", "action"})
VALID_STATUS = frozenset(
    {"pending", "exploring", "met", "partial", "blocked", "cancelled"}
)
VALID_SOURCES = frozenset({"seed", "user", "discovered"})


def validate_flows(data: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Errors block execution; warnings allow queued seeds."""
    errors: list[str] = []
    warnings: list[str] = []
    flows = data.get("flows")
    if flows is None:
        errors.append("missing 'flows' array")
        return errors, warnings
    if not isinstance(flows, list):
        errors.append("'flows' must be an array")
        return errors, warnings

    by_id: dict[str, dict[str, Any]] = {}
    for i, flow in enumerate(flows):
        if not isinstance(flow, dict):
            errors.append(f"flows[{i}]: not an object")
            continue
        fid = flow.get("id")
        if not fid:
            errors.append(f"flows[{i}]: missing id")
            continue
        if fid in by_id:
            errors.append(f"duplicate id: {fid}")
        by_id[str(fid)] = flow

        kind = flow.get("kind")
        if kind not in VALID_KINDS:
            errors.append(f"{fid}: invalid kind '{kind}'")
        status = flow.get("status")
        if status not in VALID_STATUS:
            errors.append(f"{fid}: invalid status '{status}'")
        source = flow.get("source")
        if source and source not in VALID_SOURCES:
            errors.append(f"{fid}: invalid source '{source}'")
        if kind == "entry" and flow.get("subtree_discovered") is None:
            errors.append(f"{fid}: entry should have subtree_discovered (bool)")
        if kind == "action" and flow.get("subtree_discovered") is not None:
            errors.append(f"{fid}: action must not have subtree_discovered")

    for fid, flow in by_id.items():
        parent_id = flow.get("parent_id")
        if not parent_id:
            if flow.get("kind") == "action" and flow.get("source") == "discovered":
                errors.append(f"{fid}: discovered action should have parent_id")
            continue
        parent = by_id.get(str(parent_id))
        if not parent:
            errors.append(f"{fid}: parent_id '{parent_id}' not found")
            continue
        if parent.get("kind") != "entry":
            errors.append(f"{fid}: parent {parent_id} must be kind entry")
            continue
        if flow.get("kind") != "action":
            continue
        parent_status = parent.get("status")
        child_status = flow.get("status")
        if parent_status in ("met", "exploring"):
            continue
        msg = (
            f"{fid}: parent {parent_id} should be met/exploring before action "
            f"(parent status={parent_status})"
        )
        if child_status in ("exploring", "met", "partial"):
            errors.append(msg)
        else:
            warnings.append(msg)

    cycle = data.get("cycle") or {}
    scope = cycle.get("discover_scope")
    if scope and not isinstance(scope, dict):
        errors.append("cycle.discover_scope must be an object")
    elif scope:
        pid = scope.get("parent_flow_id")
        if pid and pid not in by_id:
            errors.append(f"discover_scope.parent_flow_id '{pid}' not in flows")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", help="Path to flows.json")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat parent-order warnings as errors",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.path:
        path = Path(args.path)
        if not path.is_absolute():
            path = root / path
    else:
        state_path = root / ".cursor/mcp-improvement-cycle/state.json"
        if not state_path.is_file():
            print("No flows path and no state.json", file=sys.stderr)
            return 1
        state = json.loads(state_path.read_text(encoding="utf-8-sig"))
        active_run = state.get("active_run")
        if not active_run:
            print("active_run not set", file=sys.stderr)
            return 1
        path = root / ".cursor/mcp-improvement-cycle/runs" / str(active_run) / "flows.json"

    if not path.is_file():
        print(f"Not found: {path}", file=sys.stderr)
        return 1

    data = json.loads(path.read_text(encoding="utf-8-sig"))
    errors, warnings = validate_flows(data)
    if args.strict:
        errors = errors + warnings
        warnings = []
    if warnings:
        print(f"flows.json warnings ({path}):", file=sys.stderr)
        for warn in warnings:
            print(f"  - {warn}", file=sys.stderr)
    if errors:
        print(f"flows.json INVALID ({path}):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    n = len(data.get("flows") or [])
    suffix = f" ({len(warnings)} warnings)" if warnings else ""
    print(f"OK — {n} flows in {path}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

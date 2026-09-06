#!/usr/bin/env python3
"""Validate detection/data/uia_control_map.json against Microsoft UIA control types.

Ensures every official MS control type is present, JSON schema is sane, and
referenced MCP tool names exist in the known catalog.

Usage:
    python scripts/validate_uia_control_map.py
    python scripts/validate_uia_control_map.py --list   # print mapped types
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_DIR = REPO_ROOT / "mcp-servers" / "awdui-server"
MAP_PATH = SERVER_DIR / "detection" / "data" / "uia_control_map.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true", help="List control types in JSON")
    args = parser.parse_args()

    sys.path.insert(0, str(SERVER_DIR))
    from detection.uia_control_map import (  # noqa: E402
        ALLOWED_EXTRA_CONTROL_TYPES,
        OFFICIAL_MS_CONTROL_TYPES,
        list_control_types,
        load_control_map,
        validate_control_map,
    )

    if args.list:
        data = load_control_map()
        for name in list_control_types():
            spec = data["controls"][name]
            pms = spec.get("patterns_ms") or {}
            must = len(pms.get("must") or [])
            cond = len(pms.get("conditional") or [])
            tag = "MS" if name in OFFICIAL_MS_CONTROL_TYPES else "extra"
            print(f"{name:16}  {tag}  must={must} conditional={cond}")
        print(f"\nTotal: {len(list_control_types())} ({len(OFFICIAL_MS_CONTROL_TYPES)} official MS)")
        return 0

    if not MAP_PATH.exists():
        print(f"Missing map file: {MAP_PATH}", file=sys.stderr)
        return 1

    errors = validate_control_map()
    if errors:
        print("UIA CONTROL MAP INVALID\n", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        print(
            f"\nFix: python scripts/sync_uia_control_map.py --apply "
            f"or update {MAP_PATH.relative_to(REPO_ROOT)}",
            file=sys.stderr,
        )
        return 1

    n = len(load_control_map()["controls"])
    extras = ", ".join(sorted(ALLOWED_EXTRA_CONTROL_TYPES))
    print(f"OK — {n} control types ({len(OFFICIAL_MS_CONTROL_TYPES)} MS official + extras: {extras})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

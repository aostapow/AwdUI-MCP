#!/usr/bin/env python3
"""Conservative sync between Microsoft UIA patterns and uia_control_map.json.

Does NOT overwrite curated read/act/fallback strategies. Only:
  --check            Report missing types, extras, and patterns_ms drift
  --apply            Add stub entries for MS types missing from the map
  --fetch-reference  Refresh ms_uia_patterns_reference.json from Microsoft Learn

Usage:
    python scripts/sync_uia_control_map.py --check
    python scripts/sync_uia_control_map.py --apply
    python scripts/sync_uia_control_map.py --fetch-reference
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_DIR = REPO_ROOT / "mcp-servers" / "awdui-server"
MAP_PATH = SERVER_DIR / "detection" / "data" / "uia_control_map.json"
REFERENCE_PATH = SERVER_DIR / "detection" / "data" / "ms_uia_patterns_reference.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync UIA control map with MS reference")
    parser.add_argument("--check", action="store_true", help="Report drift (default if no mode)")
    parser.add_argument("--apply", action="store_true", help="Add missing MS types as stubs")
    parser.add_argument(
        "--fetch-reference",
        action="store_true",
        help="Download MS pattern table into ms_uia_patterns_reference.json",
    )
    parser.add_argument("--strict", action="store_true", help="Exit 1 on any drift (not only missing)")
    args = parser.parse_args()

    if not args.check and not args.apply and not args.fetch_reference:
        args.check = True

    sys.path.insert(0, str(SERVER_DIR))
    from detection.ms_uia_sync import (  # noqa: E402
        apply_missing_controls,
        compare_maps,
        fetch_ms_pattern_reference,
        format_report,
        load_control_map_raw,
        load_patterns_reference,
        write_json,
    )
    from detection.uia_control_map import ALLOWED_EXTRA_CONTROL_TYPES, validate_control_map  # noqa: E402

    if args.fetch_reference:
        existing = load_patterns_reference(REFERENCE_PATH)
        ref = fetch_ms_pattern_reference(existing=existing)
        write_json(REFERENCE_PATH, ref)
        print(f"Updated reference: {REFERENCE_PATH.relative_to(REPO_ROOT)} ({len(ref['controls'])} types)")
        print("Next: python scripts/sync_uia_control_map.py --check")

    reference = load_patterns_reference(REFERENCE_PATH)
    map_data = load_control_map_raw(MAP_PATH)
    report = compare_maps(map_data, reference, ALLOWED_EXTRA_CONTROL_TYPES)

    if args.apply:
        if not report.missing_in_map:
            print("Nothing to apply — map already has all MS control types.")
        else:
            added = apply_missing_controls(map_data, reference)
            write_json(MAP_PATH, map_data)
            errors = validate_control_map(map_data)
            if errors:
                print("Applied stubs but validation failed:\n", file=sys.stderr)
                for err in errors:
                    print(f"  - {err}", file=sys.stderr)
                return 1
            print(f"Added {len(added)} stub(s) to {MAP_PATH.relative_to(REPO_ROOT)}:")
            for role in added:
                print(f"  + {role}")
            print("\nCurate read/act/fallback for new entries, then run validate_uia_control_map.py")
            report = compare_maps(map_data, reference, ALLOWED_EXTRA_CONTROL_TYPES)

    if args.check or args.apply:
        print(format_report(report, reference, map_data))

    if report.needs_apply:
        return 1
    if args.strict and report.has_warnings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

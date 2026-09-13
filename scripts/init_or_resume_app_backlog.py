#!/usr/bin/env python3
"""Create or resume per-app lab backlog. Updates state.json pointers.

Usage:
  python scripts/init_or_resume_app_backlog.py "Calculadora"
  python scripts/init_or_resume_app_backlog.py "Calculadora" --import-flows runs/calculadora-2026-09-11/flows.json
  python scripts/init_or_resume_app_backlog.py "Calculadora" --run-id calculadora-2026-09-11
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from app_backlog_lib import init_or_resume, REPO_ROOT  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Init or resume app lab backlog")
    parser.add_argument("app_name", help='Display name, e.g. "Calculadora"')
    parser.add_argument(
        "--import-flows",
        type=Path,
        help="flows.json to import on first create only",
    )
    parser.add_argument("--run-id", help="Active run folder name under runs/")
    parser.add_argument("--json", action="store_true", help="Print result JSON")
    args = parser.parse_args()

    import_path = args.import_flows
    if import_path and not import_path.is_absolute():
        import_path = REPO_ROOT / import_path

    result = init_or_resume(
        args.app_name,
        import_flows_path=import_path,
        run_id=args.run_id,
    )
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        action = "CREATED" if result["created"] else "RESUMED"
        prog = result.get("progress") or {}
        nxt = result.get("next_item") or {}
        print(f"{action} backlog for {result['app_name']} (slug={result['app_slug']})")
        print(f"  path: {result['backlog_path']}")
        print(f"  run_id: {result['run_id']}")
        print(
            f"  progress: done={prog.get('done')} pending={prog.get('pending')} "
            f"complete={prog.get('complete')}"
        )
        if nxt:
            print(f"  next: {nxt.get('id')} — {nxt.get('title')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

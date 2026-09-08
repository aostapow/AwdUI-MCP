#!/usr/bin/env python3
"""Generate coverage.json + lab-summary.md for a lab run directory."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lab_coverage_lib import REPO_ROOT, build_lab_report, write_lab_report  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Lab coverage report for a run folder")
    parser.add_argument(
        "run_dir",
        nargs="?",
        help="Path to runs/{run_id} (default: from state.json active_run)",
    )
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()

    if args.run_dir:
        run_dir = Path(args.run_dir)
        if not run_dir.is_absolute():
            run_dir = REPO_ROOT / run_dir
    else:
        state_path = REPO_ROOT / ".cursor" / "mcp-improvement-cycle" / "state.json"
        if not state_path.is_file():
            print("No run_dir and no state.json", file=sys.stderr)
            return 1
        state = json.loads(state_path.read_text(encoding="utf-8-sig"))
        active_run = state.get("active_run")
        if not active_run:
            print("active_run not set in state.json", file=sys.stderr)
            return 1
        run_dir = REPO_ROOT / ".cursor" / "mcp-improvement-cycle" / "runs" / str(active_run)

    if not run_dir.is_dir():
        print(f"Run directory not found: {run_dir}", file=sys.stderr)
        return 1

    json_path, md_path = write_lab_report(run_dir)
    print(f"OK — {json_path}")
    if not args.json_only:
        print(f"OK — {md_path}")
    report = build_lab_report(run_dir)
    mt = report["usage"]["mcp_tools"]
    print(
        f"Coverage: tools {mt['used_total']}/{mt['universe_total']} ({mt['coverage_pct']}%)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

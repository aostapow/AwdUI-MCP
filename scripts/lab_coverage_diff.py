#!/usr/bin/env python3
"""Write coverage-diff.json/md vs previous lab run for same app."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lab_coverage_lib import REPO_ROOT, build_lab_report, write_coverage_diff  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", nargs="?", help="runs/{run_id} path")
    args = parser.parse_args()

    if args.run_dir:
        run_dir = Path(args.run_dir)
        if not run_dir.is_absolute():
            run_dir = REPO_ROOT / run_dir
    else:
        state_path = REPO_ROOT / ".cursor/mcp-improvement-cycle/state.json"
        state = json.loads(state_path.read_text(encoding="utf-8-sig"))
        run_dir = (
            REPO_ROOT
            / ".cursor/mcp-improvement-cycle/runs"
            / str(state.get("active_run"))
        )

    if not run_dir.is_dir():
        print(f"Not found: {run_dir}", file=sys.stderr)
        return 1

    out = write_coverage_diff(run_dir)
    if out is None:
        print("No previous run with coverage.json for same app")
        return 0
    print(f"OK — {out}")
    print(f"OK — {run_dir / 'coverage-diff.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

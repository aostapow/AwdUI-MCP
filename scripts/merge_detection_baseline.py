#!/usr/bin/env python3
"""Merge all lab runs' mcp-usage.jsonl into detection_baseline.json."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from detection_baseline_lib import (  # noqa: E402
    DEFAULT_BASELINE_PATH,
    discover_run_dirs,
    merge_runs,
    write_baseline,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build detection baseline manifest from lab runs.")
    parser.add_argument(
        "--runs-dir",
        type=Path,
        default=None,
        help="Default: .cursor/mcp-improvement-cycle/runs",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_BASELINE_PATH,
        help="Output JSON path",
    )
    parser.add_argument("--run", action="append", dest="run_ids", help="Only these run folder names")
    args = parser.parse_args()

    all_dirs = discover_run_dirs(args.runs_dir)
    if args.run_ids:
        wanted = set(args.run_ids)
        all_dirs = [p for p in all_dirs if p.name in wanted]
    if not all_dirs:
        print("no runs with mcp-usage.jsonl found")
        data = merge_runs([])
        write_baseline(args.output, data)
        return 0

    data = merge_runs(all_dirs)
    write_baseline(args.output, data)
    n_cells = len(data.get("cells") or {})
    print(f"wrote {args.output} ({n_cells} cells from {len(data.get('source_runs') or [])} runs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

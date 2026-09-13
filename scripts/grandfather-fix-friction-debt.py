#!/usr/bin/env python3
"""Mark historical lab friction lines as legacy_debt (pre fix-in-cycle gate).

Use once per run when re-resuming a lab with many fix_in_cycle=not_attempted lines
that will not be re-fixed retroactively.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "improvements_jsonl",
        type=Path,
        help="Path to runs/<id>/improvements.jsonl",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    path = args.improvements_jsonl
    if not path.is_file():
        print(f"not found: {path}")
        return 1
    out_lines: list[str] = []
    changed = 0
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        t = str(obj.get("type") or obj.get("kind") or "").lower()
        fic = str(obj.get("fix_in_cycle") or "").lower()
        if t in ("friction", "gap") and fic == "not_attempted":
            obj["fix_in_cycle"] = "legacy_debt"
            obj["legacy_debt_note"] = "grandfathered before fix_in_cycle gate"
            changed += 1
        out_lines.append(json.dumps(obj, ensure_ascii=False))
    if args.dry_run:
        print(f"would update {changed} lines in {path}")
        return 0
    path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print(f"updated {changed} lines in {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

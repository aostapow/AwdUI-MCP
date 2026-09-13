#!/usr/bin/env python3
"""Analyze property_observations stability for repository objects."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp-servers" / "awdui-server"))
sys.path.insert(0, str(ROOT / "scripts"))

from detection import repo_store  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Repo property stability report")
    parser.add_argument("--app", default="Calculadora", help="Application name in repo")
    parser.add_argument("--repo-path", help="Single repo_path (e.g. Calculadora/num2Button)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.repo_path:
        stats = repo_store.identification_stats_for_repo_path(args.repo_path, args.app)
        out = stats
    else:
        objs = repo_store.list_objects_for_app(args.app)
        out = {
            "app": args.app,
            "objects": [],
        }
        for o in objs:
            rp = o.get("repo_path") or ""
            if not rp:
                continue
            oid_row = repo_store.identification_stats_for_repo_path(rp, args.app)
            if oid_row.get("found"):
                out["objects"].append(oid_row)

    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        if args.repo_path:
            print(json.dumps(out, indent=2, ensure_ascii=False))
        else:
            for item in out.get("objects", []):
                print(
                    f"{item['repo_path']}: samples={item.get('samples')} "
                    f"stable={item.get('stable')} volatile={item.get('volatile')}"
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

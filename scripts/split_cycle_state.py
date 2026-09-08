#!/usr/bin/env python3
"""Extract large matrices from state.json into separate files (one-time / maintenance)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".cursor" / "mcp-improvement-cycle" / "state.json"
MATRICES = ROOT / ".cursor" / "mcp-improvement-cycle" / "matrices"


def main() -> int:
    if not STATE.exists():
        print(f"missing {STATE}")
        return 1
    data = json.loads(STATE.read_text(encoding="utf-8-sig"))
    MATRICES.mkdir(parents=True, exist_ok=True)
    moved = []
    for key in ("teams_matrix", "tool_validation_matrix"):
        if key not in data:
            continue
        out_path = MATRICES / f"{key}.json"
        out_path.write_text(json.dumps(data[key], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        data[f"{key}_ref"] = f"matrices/{key}.json"
        del data[key]
        moved.append(key)
    if moved:
        STATE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"split: {', '.join(moved)} -> {MATRICES}")
    else:
        print("nothing to split (refs already present or matrices missing)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

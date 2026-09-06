#!/usr/bin/env python3
"""Orchestrator — runs Calculator coverage until state.json says complete.

Pattern: durable state file + explicit completion criteria (not LLM self-report).
See .cursor/skills/calculator-mcp-harness/SKILL.md
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".cursor" / "calculator-coverage" / "state.json"
PY = Path.home() / ".awdui-mcp" / ".venv" / "Scripts" / "python.exe"
if not PY.is_file():
    PY = Path(sys.executable)

STEPS = [
    ("full_catalog", [str(PY), str(ROOT / "scripts" / "explore_calculator_full.py")]),
    ("pytest", [str(PY), "-m", "pytest",
                str(ROOT / "tests" / "integration" / "test_calculator_coverage.py"),
                str(ROOT / "tests" / "integration" / "test_calculator.py"),
                "-q", "--tb=line"]),
]


def main() -> int:
    import os
    import sys

    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT))
    from tests.integration.gui_session import require_supervised_session

    require_supervised_session("calculator_orchestrator.py")
    os.environ["AWDUI_GUI_SESSION"] = "1"
    os.environ["AWDUI_SKIP_VIRTUAL_DESKTOP"] = "1"

    if not STATE.is_file():
        print(f"[FAIL] missing state file: {STATE}")
        return 1

    state = json.loads(STATE.read_text(encoding="utf-8"))
    if state.get("status") == "complete":
        print("[OK] already complete per state.json")
        return 0

    print(f"Goal: {state.get('goal')}")
    print(f"Criteria: {state.get('completion_criteria')}")

    for name, cmd in STEPS:
        print(f"\n=== {name} ===")
        env = {**os.environ, "AWDUI_GUI_SESSION": "1"}
        rc = subprocess.call(cmd, cwd=str(ROOT), env=env)
        if rc != 0:
            state["status"] = "blocked"
            state.setdefault("blockers", []).append(f"{name} exit={rc}")
            STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")
            print(f"[BLOCKED] {name} failed — fix and re-run orchestrator")
            return rc

    state["status"] = "complete"
    for t in state.get("tasks", []):
        if t.get("status") in ("pending", "in_progress", "blocked"):
            t["status"] = "done"
    STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print("\n[OK] Calculator coverage COMPLETE per state.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run full Calculator coverage suite until complete — gate script."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = Path.home() / ".awdui-mcp" / ".venv" / "Scripts" / "python.exe"
if not PY.is_file():
    PY = Path(sys.executable)


def main() -> int:
    import os
    import sys

    sys.path.insert(0, str(ROOT))
    from tests.integration.gui_session import require_supervised_session

    require_supervised_session("run_calculator_coverage.py")
    os.environ["AWDUI_GUI_SESSION"] = "1"
    os.environ["AWDUI_SKIP_VIRTUAL_DESKTOP"] = "1"
    steps = [
        ("explore modes", [str(PY), str(ROOT / "scripts" / "explore_calculator_modes.py")]),
        ("integration tests", [str(PY), "-m", "pytest", str(ROOT / "tests" / "integration" / "test_calculator_coverage.py"),
                               str(ROOT / "tests" / "integration" / "test_calculator.py"), "-q", "--tb=short"]),
    ]
    for name, cmd in steps:
        print(f"\n=== {name} ===")
        env = {**os.environ, "AWDUI_GUI_SESSION": "1"}
        rc = subprocess.call(cmd, cwd=str(ROOT), env=env)
        if rc != 0:
            print(f"[FAIL] {name} exit={rc}")
            return rc
    print("\n[OK] Calculator coverage gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

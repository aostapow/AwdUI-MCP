#!/usr/bin/env python3
"""Quick Calculator smoke — launch, element check, 2+2=4 with evidence."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "mcp-servers" / "awdui-server"
sys.path.insert(0, str(SERVER))
sys.path.insert(0, str(ROOT))

_VENV = Path.home() / ".awdui-mcp" / ".venv" / "Lib" / "site-packages"
if _VENV.is_dir():
    sys.path.insert(0, str(_VENV))


def main() -> int:
    from tests.integration.gui_session import require_supervised_session

    require_supervised_session("smoke_calculator.py")

    if sys.platform != "win32":
        print("[SKIP] Windows only")
        return 0

    import tempfile
    from screenshot_manager import ScreenshotManager
    from tools import screenshot as screenshot_mod
    if screenshot_mod.screenshot_manager is None:
        screenshot_mod.screenshot_manager = ScreenshotManager(
            os.path.join(tempfile.gettempdir(), "awdui_screenshots")
        )

    from tests.integration.calculator_harness import (
        IDS,
        ensure_calculator_running,
        teardown_calculator,
    )
    from tests.integration.evidence import compute_and_verify, capture_evidence
    from tools.ui_automation import do_find_element

    ok = True
    try:
        ctx = ensure_calculator_running()
        if not ctx.get("success"):
            print(f"[FAIL] launch: {ctx.get('error')}")
            return 1
        title = ctx["window_title"]
        print(f"[OK] launch target={title}")

        found = do_find_element(automation_id="num1Button", window_title=title)
        if not found.get("found"):
            print("[FAIL] num1Button not found")
            ok = False
        else:
            print("[OK] element_exists num1Button")

        result = compute_and_verify(
            [
                ("clear", IDS["clear"]),
                ("2", "2"),
                ("plus", IDS["plus"]),
                ("2", "2"),
                ("equals", IDS["equals"]),
            ],
            "4",
            "smoke-2plus2",
            window_title=title,
        )
        print(f"[OK] 2+2=4 source={result.get('source')} actual={result.get('actual')}")
        shot = capture_evidence("smoke_final", title)
        if shot:
            print(f"[OK] evidence screenshot={shot}")
    except Exception as exc:
        print(f"[FAIL] {exc}")
        ok = False
    finally:
        teardown_calculator()

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

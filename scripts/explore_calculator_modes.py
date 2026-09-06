#!/usr/bin/env python3
"""Explore all Calculator modes — dump UIA button inventory to JSON."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "mcp-servers" / "awdui-server"
sys.path.insert(0, str(SERVER))
sys.path.insert(0, str(ROOT))
os.environ.setdefault("AWDUI_SKIP_VIRTUAL_DESKTOP", "1")

_VENV = Path.home() / ".awdui-mcp" / ".venv" / "Lib" / "site-packages"
if _VENV.is_dir():
    sys.path.insert(0, str(_VENV))

OUT = ROOT / "tests" / "integration" / "evidence" / "mode_map.json"


def main() -> int:
    from tests.integration.gui_session import begin, end, require_supervised_session

    require_supervised_session("explore_calculator_modes.py")
    begin(name="explore_calculator_modes", max_clicks=200, max_seconds=600)

    from tests.integration.calculator_harness import (
        ensure_calculator_running,
        get_current_mode,
        inventory_buttons,
        switch_mode,
        teardown_calculator,
    )
    from tests.integration.calculator_map import MODE_ORDER, NAV_MODES

    ctx = ensure_calculator_running()
    if not ctx.get("success"):
        print(f"[FAIL] {ctx.get('error')}")
        return 1

    title = ctx["window_title"]
    report: dict = {"window_title": title, "modes": {}}

    for mode_id in MODE_ORDER:
        print(f"[explore] mode={mode_id}...")
        sw = switch_mode(mode_id, window_title=title)
        if not sw.get("success"):
            report["modes"][mode_id] = {"error": sw, "buttons": []}
            continue
        header = get_current_mode(title)
        buttons = inventory_buttons(title)
        report["modes"][mode_id] = {
            "header": header,
            "button_count": len(buttons),
            "buttons": buttons,
        }
        print(f"  header={header!r} buttons={len(buttons)}")

    # Settings (footer item)
    print("[explore] mode=SettingsItem...")
    switch_mode("SettingsItem", window_title=title)
    report["modes"]["SettingsItem"] = {
        "header": get_current_mode(title),
        "buttons": inventory_buttons(title),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] wrote {OUT}")
    teardown_calculator()
    end()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

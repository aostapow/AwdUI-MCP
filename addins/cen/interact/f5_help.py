"""F5 catalog help automation."""
from __future__ import annotations

import json
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional


@lru_cache(maxsize=1)
def _constants() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "knowledge" / "controls.json"
    return json.loads(path.read_text(encoding="utf-8")).get("constants", {})


def trigger_f5(
    automation_id: str = "",
    name: str = "",
    window_title: Optional[str] = None,
    wait_ms: int = 800,
) -> dict[str, Any]:
    aid = (automation_id or name or "").strip()
    if not aid:
        return {"success": False, "error": "automation_id or name required"}

    from tools.ui_automation import do_click_element
    from tools.input_tools import do_press_key

    focus = do_click_element(automation_id=aid, window_title=window_title or "")
    key = do_press_key("F5")

    if wait_ms > 0:
        time.sleep(wait_ms / 1000.0)

    from lookup import detect_lookup_modal

    modal = detect_lookup_modal(window_title)
    return {
        "success": True,
        "field": aid,
        "f5_keycode": _constants().get("f5_keycode", 116),
        "focus": focus,
        "key": key,
        "lookup": modal,
    }

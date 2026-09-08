"""Wait for COBIS field validation / RPC (toolbar enable, Leave)."""
from __future__ import annotations

import time
from typing import Any, Optional

from toolbar import list_cobis_toolbar


def wait_toolbar_enabled(
    caption: str = "Buscar",
    window_title: Optional[str] = None,
    timeout_ms: int = 8000,
    poll_ms: int = 400,
) -> dict[str, Any]:
    """Poll until toolbar button (usually Buscar) becomes enabled after msk*/txt* Leave."""
    cap = (caption or "Buscar").lower().replace("&", "")
    deadline = time.time() + timeout_ms / 1000.0
    last = None
    while time.time() < deadline:
        tb = list_cobis_toolbar(window_title)
        last = tb
        for btn in tb.get("buttons") or []:
            name = (btn.get("name") or "").lower().replace("&", "")
            if cap in name or name in cap:
                if btn.get("enabled", True):
                    return {
                        "success": True,
                        "button": btn,
                        "elapsed_ms": int((deadline - time.time() + timeout_ms / 1000) * 1000),
                        "resolved_window_title": tb.get("resolved_window_title") or "",
                    }
        time.sleep(poll_ms / 1000.0)

    return {
        "success": False,
        "error": f"toolbar '{caption}' not enabled within {timeout_ms}ms",
        "last_toolbar": last,
    }


def wait_field_stable(
    automation_id: str = "",
    name: str = "",
    window_title: Optional[str] = None,
    stable_reads: int = 2,
    timeout_ms: int = 6000,
) -> dict[str, Any]:
    """Poll field read until value stable (post-RPC account validation)."""
    from interact.fields import read_field

    aid = automation_id or name
    if not aid:
        return {"success": False, "error": "automation_id or name required"}

    deadline = time.time() + timeout_ms / 1000.0
    prev = None
    stable = 0
    last_read = None
    while time.time() < deadline:
        last_read = read_field(automation_id, name, window_title, use_clip_text=True)
        val = last_read.get("value") or ""
        if val and val == prev:
            stable += 1
            if stable >= stable_reads:
                return {
                    "success": True,
                    "stable_value": val,
                    "reads": stable_reads,
                    "field": aid,
                }
        else:
            stable = 0
        prev = val
        time.sleep(0.35)

    return {
        "success": False,
        "error": "field value did not stabilize",
        "last_read": last_read,
    }

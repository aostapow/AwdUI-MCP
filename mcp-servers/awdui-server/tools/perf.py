"""Performance toggles for AwdUI MCP (fast by default).

Set AWDUI_VERIFY=1 to restore pre-click screenshot comparison and slower paths.
Set AWDUI_SNAPSHOT=1 to capture full object snapshots on every smart_find remember.
"""
from __future__ import annotations

import os


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    return default


def is_fast_mode() -> bool:
    """Fast paths enabled unless AWDUI_VERIFY=1."""
    return not _env_flag("AWDUI_VERIFY", default=False)


def verify_visual_changes() -> bool:
    """Before/after screenshot diff on click/scroll."""
    return _env_flag("AWDUI_VERIFY", default=False)


def remember_snapshots() -> bool:
    """Full image snapshot on smart_find remember."""
    return _env_flag("AWDUI_SNAPSHOT", default=False)


def focus_cache_ttl() -> float:
    try:
        return float(os.environ.get("AWDUI_FOCUS_TTL", "3.0"))
    except ValueError:
        return 3.0

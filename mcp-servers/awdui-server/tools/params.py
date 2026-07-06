"""Shared MCP tool parameter helpers."""
from __future__ import annotations

from typing import Optional


def resolve_window_title(
    window_title: str = "",
    title: str = "",
) -> Optional[str]:
    """Accept ``window_title`` or ``title`` (either may be used by MCP clients)."""
    value = (window_title or title or "").strip()
    return value or None

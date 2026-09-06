"""Shared MCP tool parameter helpers."""
from __future__ import annotations

from typing import Optional, Tuple


def resolve_window_title(
    window_title: str = "",
    title: str = "",
) -> Optional[str]:
    """Accept ``window_title`` or ``title`` (either may be used by MCP clients)."""
    value = (window_title or title or "").strip()
    return value or None


def resolve_scoped_window(
    app_id: str = "",
    window_title: str = "",
    title: str = "",
    window_handle: int = 0,
) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    """Merge app_id session with explicit window title/hwnd.

    Returns (window_title, window_handle, error_message).
    """
    from tools.app_session import resolve_scope

    wt, hwnd, err = resolve_scope(
        app_id=app_id,
        window_title=resolve_window_title(window_title, title),
        window_handle=window_handle or None,
    )
    if err:
        return wt, hwnd, str(err.get("error") or "Unknown app_id")
    return wt, hwnd, None

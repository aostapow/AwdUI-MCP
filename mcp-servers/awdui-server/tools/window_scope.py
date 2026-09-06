"""Resolve automation window scope (target + modal children)."""
from __future__ import annotations

from typing import Any, Optional


def resolve_window_scope(window_title: Optional[str] = None) -> dict[str, Any]:
    from tools.target_window import get_target

    title = (window_title or get_target() or "").strip()
    return {
        "requested_title": window_title or "",
        "resolved_title": title,
        "has_target": bool(title),
    }

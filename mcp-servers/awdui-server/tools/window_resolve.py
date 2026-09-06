"""Normalize window_title / window_handle for scoped UIA operations."""
from __future__ import annotations

from typing import Any, Optional


def normalize_window_target(
    window_title: Optional[str] = None,
    window_handle: Optional[int] = None,
) -> dict[str, Any]:
    title = (window_title or "").strip()
    hwnd = int(window_handle or 0)
    out: dict[str, Any] = {
        "window_title": title,
        "window_handle": hwnd,
        "scope_hwnd": hwnd if hwnd > 0 else 0,
    }
    if hwnd > 0:
        from detection.hwnd_scope import resolve_window_from_hwnd

        hit = resolve_window_from_hwnd(hwnd)
        out["hwnd_meta"] = hit
        if hit.get("success") and not title:
            out["window_title"] = hit.get("title") or ""
    return out

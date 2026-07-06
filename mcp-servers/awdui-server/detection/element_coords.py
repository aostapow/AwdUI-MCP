"""Normalize element bounding boxes to physical screen coordinates."""
from __future__ import annotations

from typing import Optional


def window_region(window_title: Optional[str]) -> Optional[dict]:
    if not window_title:
        return None
    try:
        from tools.screenshot import _region_for_window

        return _region_for_window(window_title)
    except Exception:
        return None


def is_window_relative_bbox(
    x: int,
    y: int,
    w: int,
    h: int,
    region: dict,
) -> bool:
    return (
        x >= 0
        and y >= 0
        and w > 0
        and h > 0
        and x + w <= int(region["w"]) + 12
        and y + h <= int(region["h"]) + 12
    )


def _dpi_scale_for(window_title: Optional[str]) -> float:
    try:
        from tools.screenshot import get_dpi_scale

        scale = float(get_dpi_scale())
    except Exception:
        scale = 1.0
    if window_title:
        try:
            from tools.windows import find_matching_window, do_list_windows

            match = find_matching_window(window_title, do_list_windows())
            win = match.get("window") or {}
            if win.get("dpi_scale"):
                return float(win["dpi_scale"])
        except Exception:
            pass
    return scale


def _inside_region(px: int, py: int, region: dict) -> bool:
    return (
        int(region["x"]) <= px < int(region["x"]) + int(region["w"])
        and int(region["y"]) <= py < int(region["y"]) + int(region["h"])
    )


def to_screen_coords(elem: dict, window_title: Optional[str] = None) -> dict:
    """Return *elem* with x/y/width/height/clickable center in physical screen space."""
    out = dict(elem)
    w = int(out.get("width") or out.get("w") or 0)
    h = int(out.get("height") or out.get("h") or 0)
    x = int(out.get("x", 0) or 0)
    y = int(out.get("y", 0) or 0)
    if w <= 0 or h <= 0:
        return out

    region = window_region(window_title)
    if not region:
        return _apply_clickable_center(out)

    if is_window_relative_bbox(x, y, w, h, region):
        sx = x + int(region["x"])
        sy = y + int(region["y"])
        out["x"] = sx
        out["y"] = sy
        return _apply_clickable_center(out)

    scale = _dpi_scale_for(window_title)
    if scale != 1.0 and not _inside_region(x, y, region):
        try:
            from tools.screenshot import logical_to_physical

            px, py = logical_to_physical(x, y, scale)
            pw, ph = logical_to_physical(w, h, scale)
            if _inside_region(px, py, region):
                out["x"] = px
                out["y"] = py
                out["width"] = pw
                out["height"] = ph
        except Exception:
            pass

    return _apply_clickable_center(out)


def _apply_clickable_center(elem: dict) -> dict:
    out = dict(elem)
    x = int(out.get("x", 0) or 0)
    y = int(out.get("y", 0) or 0)
    w = int(out.get("width") or out.get("w") or 0)
    h = int(out.get("height") or out.get("h") or 0)
    if w > 0 and h > 0:
        cx = x + w // 2
        cy = y + h // 2
        out["clickable_x"] = cx
        out["clickable_y"] = cy
        out["center_x"] = cx
        out["center_y"] = cy
    return out


def click_coords(elem: dict, window_title: Optional[str] = None) -> tuple[int, int]:
    """Physical screen coordinates for clicking the element center."""
    normalized = to_screen_coords(elem, window_title)
    cx = normalized.get("clickable_x")
    cy = normalized.get("clickable_y")
    if cx is not None and cy is not None:
        return int(cx), int(cy)
    return (
        int(normalized.get("x", 0)) + int(normalized.get("width", 0)) // 2,
        int(normalized.get("y", 0)) + int(normalized.get("height", 0)) // 2,
    )

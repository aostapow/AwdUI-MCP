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


_MARGIN = 12


def is_window_relative_bbox(
    x: int,
    y: int,
    w: int,
    h: int,
    region: dict,
    *,
    scale: float = 1.0,
) -> bool:
    """True when *x/y/w/h* fit inside the window content box (logical or physical)."""
    if x < 0 or y < 0 or w <= 0 or h <= 0:
        return False
    rw = int(region["w"])
    rh = int(region["h"])
    if x + w <= rw + _MARGIN and y + h <= rh + _MARGIN:
        return True
    if scale > 1.0:
        lw = int(rw / scale)
        lh = int(rh / scale)
        return x + w <= lw + _MARGIN and y + h <= lh + _MARGIN
    return False


def _fits_logical_window_relative(
    x: int,
    y: int,
    w: int,
    h: int,
    region: dict,
    scale: float,
) -> bool:
    if scale <= 1.0:
        return is_window_relative_bbox(x, y, w, h, region, scale=1.0)
    lw = int(int(region["w"]) / scale)
    lh = int(int(region["h"]) / scale)
    return (
        x >= 0
        and y >= 0
        and x + w <= lw + _MARGIN
        and y + h <= lh + _MARGIN
    )


def _fits_physical_window_relative(
    x: int,
    y: int,
    w: int,
    h: int,
    region: dict,
) -> bool:
    rw = int(region["w"])
    rh = int(region["h"])
    return (
        x >= 0
        and y >= 0
        and x + w <= rw + _MARGIN
        and y + h <= rh + _MARGIN
    )


def _looks_like_screen_coords(x: int, y: int, region: dict) -> bool:
    """FlaUI / pywinauto return absolute physical screen coordinates."""
    return _inside_region(x, y, region)


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

    rx, ry = int(region["x"]), int(region["y"])
    scale = _dpi_scale_for(window_title)

    # Logical window-relative (UIA at custom DPI). Always scale before offset.
    if _fits_logical_window_relative(x, y, w, h, region, scale):
        if scale != 1.0:
            try:
                from tools.screenshot import logical_to_physical

                x, y = logical_to_physical(x, y, scale)
                w, h = logical_to_physical(w, h, scale)
            except Exception:
                pass
        out["x"] = x + rx
        out["y"] = y + ry
        out["width"] = w
        out["height"] = h
        return _apply_clickable_center(out)

    # Bottom-row logical controls may exceed lh slightly after DPI rounding.
    if scale > 1.0 and _fits_physical_window_relative(x, y, w, h, region):
        lw = int(int(region["w"]) / scale)
        lh = int(int(region["h"]) / scale)
        if x + w <= lw + _MARGIN and y < lh + _MARGIN:
            try:
                from tools.screenshot import logical_to_physical

                x, y = logical_to_physical(x, y, scale)
                w, h = logical_to_physical(w, h, scale)
            except Exception:
                pass
            out["x"] = x + rx
            out["y"] = y + ry
            out["width"] = w
            out["height"] = h
            return _apply_clickable_center(out)

    # Physical window-relative: offset only (values already match the screenshot).
    if _fits_physical_window_relative(x, y, w, h, region):
        out["x"] = x + rx
        out["y"] = y + ry
        out["width"] = w
        out["height"] = h
        return _apply_clickable_center(out)

    # Absolute screen coordinates from FlaUI / pywinauto / spy.
    if _looks_like_screen_coords(x, y, region):
        out["x"], out["y"], out["width"], out["height"] = x, y, w, h
        return _apply_clickable_center(out)

    # Logical screen coordinates outside the current window region.
    if scale != 1.0 and not _inside_region(x, y, region):
        try:
            from tools.screenshot import logical_to_physical

            x, y = logical_to_physical(x, y, scale)
            w, h = logical_to_physical(w, h, scale)
            out["x"] = x
            out["y"] = y
            out["width"] = w
            out["height"] = h
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


def screen_bbox(
    elem: dict, window_title: Optional[str] = None
) -> tuple[int, int, int, int] | None:
    """Physical screen-space bounding box after normalization."""
    if window_title is not None:
        normalized = to_screen_coords(elem, window_title)
    else:
        normalized = elem
    x = int(normalized.get("x", 0) or 0)
    y = int(normalized.get("y", 0) or 0)
    w = int(normalized.get("width") or normalized.get("w") or 0)
    h = int(normalized.get("height") or normalized.get("h") or 0)
    if w <= 0 or h <= 0:
        return None
    return x, y, w, h


def bbox_inside_window(
    screen: tuple[int, int, int, int],
    region: dict,
    margin: int = 12,
) -> bool:
    x, y, w, h = screen
    rx, ry = int(region["x"]), int(region["y"])
    rw, rh = int(region["w"]), int(region["h"])
    return (
        x >= rx - margin
        and y >= ry - margin
        and x + w <= rx + rw + margin
        and y + h <= ry + rh + margin
    )


def window_relative_bbox(
    screen: tuple[int, int, int, int], region: dict
) -> tuple[int, int, int, int]:
    x, y, w, h = screen
    return x - int(region["x"]), y - int(region["y"]), w, h


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

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


def element_center_in_rect(
    elem: dict,
    rect: dict,
    *,
    margin: int = 2,
) -> bool:
    """True when the element center lies inside a screen-space rectangle."""
    x = int(elem.get("x", 0))
    y = int(elem.get("y", 0))
    w = int(elem.get("width", 0))
    h = int(elem.get("height", 0))
    if w <= 0 or h <= 0:
        return False
    cx = x + w // 2
    cy = y + h // 2
    rx = int(rect.get("x", 0))
    ry = int(rect.get("y", 0))
    rw = int(rect.get("w", rect.get("width", 0)))
    rh = int(rect.get("h", rect.get("height", 0)))
    return (
        rx - margin <= cx < rx + rw + margin
        and ry - margin <= cy < ry + rh + margin
    )


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


def _looks_like_screen_coords(
    x: int,
    y: int,
    region: dict,
    width: int = 0,
    height: int = 0,
    *,
    margin: int = 16,
) -> bool:
    """FlaUI / pywinauto return absolute physical screen coordinates.

    UWP controls may report a top-left a few pixels left of the visual window
    rect (client vs chrome). Use the element center when width/height are known.
    """
    if width > 0 and height > 0:
        cx = x + width // 2
        cy = y + height // 2
        return _inside_region(cx, cy, region, margin=margin)
    return _inside_region(x, y, region, margin=margin)


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


def _inside_region(px: int, py: int, region: dict, margin: int = 0) -> bool:
    rx = int(region["x"]) - margin
    ry = int(region["y"]) - margin
    rw = int(region["w"]) + 2 * margin
    rh = int(region["h"]) + 2 * margin
    return rx <= px < rx + rw and ry <= py < ry + rh


def _scope_rect_for_coords(window_title: Optional[str], region: dict) -> dict:
    """Client rect when available; otherwise the visual window region."""
    if window_title:
        try:
            from detection.element_scope import resolve_window_scope

            scope = resolve_window_scope(window_title)
            if scope:
                rect = scope.get("client") or scope.get("visual")
                if rect:
                    return rect
        except Exception:
            pass
    return region


def _logical_window_relative_screen(
    x: int,
    y: int,
    w: int,
    h: int,
    region: dict,
    scale: float,
) -> tuple[int, int, int, int]:
    lx, ly, lw, lh = x, y, w, h
    if scale != 1.0:
        try:
            from tools.screenshot import logical_to_physical

            lx, ly = logical_to_physical(lx, ly, scale)
            lw, lh = logical_to_physical(lw, lh, scale)
        except Exception:
            pass
    return lx + int(region["x"]), ly + int(region["y"]), lw, lh


def _include_raw_screen_candidate(
    x: int,
    y: int,
    w: int,
    h: int,
    region: dict,
    scale: float,
) -> bool:
    """Skip raw screen when coords clearly belong to the window-relative box."""
    rx = int(region["x"])
    if x < rx:
        return True
    if not _fits_logical_window_relative(x, y, w, h, region, scale):
        return True
    return False


def _resolve_logical_screen_candidate(
    x: int,
    y: int,
    w: int,
    h: int,
    region: dict,
    scale: float,
) -> tuple[int, int, int, int] | None:
    if _fits_logical_window_relative(x, y, w, h, region, scale):
        return _logical_window_relative_screen(x, y, w, h, region, scale)
    if scale > 1.0 and _fits_physical_window_relative(x, y, w, h, region):
        lw = int(int(region["w"]) / scale)
        lh = int(int(region["h"]) / scale)
        if x + w <= lw + _MARGIN and y < lh + _MARGIN:
            return _logical_window_relative_screen(x, y, w, h, region, scale)
    return None


def _build_coord_candidates(
    x: int,
    y: int,
    w: int,
    h: int,
    region: dict,
    scale: float,
    window_title: Optional[str] = None,
) -> list[tuple[int, int, int, int]]:
    rx, ry = int(region["x"]), int(region["y"])
    candidates: list[tuple[int, int, int, int]] = []

    logical_screen = _resolve_logical_screen_candidate(x, y, w, h, region, scale)
    if logical_screen is not None:
        candidates.append(logical_screen)

    if _fits_physical_window_relative(x, y, w, h, region):
        candidates.append((x + rx, y + ry, w, h))

    logical_in_scope = (
        logical_screen is not None
        and element_center_in_rect(
            {
                "x": logical_screen[0],
                "y": logical_screen[1],
                "width": logical_screen[2],
                "height": logical_screen[3],
            },
            _scope_rect_for_coords(window_title, region),
            margin=16,
        )
    )
    # Left-column UIA coords below the visual origin are usually already screen space.
    allow_raw = _include_raw_screen_candidate(x, y, w, h, region, scale) and not (
        x < rx and logical_in_scope
    )
    if allow_raw and _looks_like_screen_coords(x, y, region, w, h):
        candidates.append((x, y, w, h))

    if scale != 1.0 and not _inside_region(x, y, region):
        try:
            from tools.screenshot import logical_to_physical

            lx, ly = logical_to_physical(x, y, scale)
            lw, lh = logical_to_physical(w, h, scale)
            candidates.append((lx, ly, lw, lh))
        except Exception:
            pass

    seen: set[tuple[int, int, int, int]] = set()
    unique: list[tuple[int, int, int, int]] = []
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            unique.append(candidate)
    return unique


def _pick_coord_candidate(
    candidates: list[tuple[int, int, int, int]],
    scope_rect: dict,
    raw_x: int,
    raw_y: int,
    w: int,
    h: int,
    region: dict,
    *,
    logical_screen: tuple[int, int, int, int] | None = None,
    logical_in_scope: bool = False,
) -> tuple[int, int, int, int] | None:
    if logical_in_scope and logical_screen and logical_screen in candidates:
        return logical_screen

    rx = int(region["x"])
    raw = (raw_x, raw_y, w, h)
    if (
        raw in candidates
        and element_center_in_rect(
            {"x": raw_x, "y": raw_y, "width": w, "height": h},
            scope_rect,
            margin=16,
        )
        and raw_x < rx
        and not logical_in_scope
    ):
        return raw

    best: tuple[int, int, int, int] | None = None
    best_score: tuple[int, int] | None = None
    for cx, cy, cw, ch in candidates:
        if (cx, cy, cw, ch) == raw:
            continue
        if not element_center_in_rect(
            {"x": cx, "y": cy, "width": cw, "height": ch},
            scope_rect,
            margin=16,
        ):
            continue
        delta = abs(cx - raw_x) + abs(cy - raw_y)
        score = (0, -delta)
        if best_score is None or score > best_score:
            best_score = score
            best = (cx, cy, cw, ch)
    if best is not None:
        return best
    if raw in candidates and element_center_in_rect(
        {"x": raw_x, "y": raw_y, "width": w, "height": h},
        scope_rect,
        margin=16,
    ):
        return raw
    return None


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

    scale = _dpi_scale_for(window_title)
    scope_rect = _scope_rect_for_coords(window_title, region)
    logical_screen = _resolve_logical_screen_candidate(x, y, w, h, region, scale)
    logical_in_scope = (
        logical_screen is not None
        and element_center_in_rect(
            {
                "x": logical_screen[0],
                "y": logical_screen[1],
                "width": logical_screen[2],
                "height": logical_screen[3],
            },
            scope_rect,
            margin=16,
        )
    )
    candidates = _build_coord_candidates(x, y, w, h, region, scale, window_title)
    picked = _pick_coord_candidate(
        candidates,
        scope_rect,
        x,
        y,
        w,
        h,
        region,
        logical_screen=logical_screen,
        logical_in_scope=logical_in_scope,
    )
    if picked is not None:
        out["x"], out["y"], out["width"], out["height"] = picked
        return _apply_clickable_center(out)

    if candidates:
        out["x"], out["y"], out["width"], out["height"] = candidates[0]
        return _apply_clickable_center(out)

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


def expander_header_click_coords(
    elem: dict, window_title: Optional[str] = None
) -> tuple[int, int]:
    """Click point on UWP expander header (upper sixth of bounding box)."""
    normalized = to_screen_coords(elem, window_title)
    x = int(normalized.get("x", 0) or 0)
    y = int(normalized.get("y", 0) or 0)
    w = int(normalized.get("width") or normalized.get("w") or 0)
    h = int(normalized.get("height") or normalized.get("h") or 0)
    if w <= 0 or h <= 0:
        return click_coords(elem, window_title)
    return x + w // 2, y + max(1, h // 6)

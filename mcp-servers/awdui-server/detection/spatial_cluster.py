"""Infer dominant on-screen content region from element spatial distribution (app-agnostic)."""
from __future__ import annotations

import time
from typing import Any, Optional, Union

from detection.element_model import DetectedElement

ElementLike = Union[DetectedElement, dict]

_SKIP_ROLES = frozenset({"Window", "Pane", "Group"})
_MAX_AREA_RATIO = 0.85
_MAX_REMOVED_RATIO = 0.4

_CONTENT_CACHE: dict[str, tuple[float, dict[str, int]]] = {}
_CACHE_TTL = 120.0


def _elem_box(elem: ElementLike) -> Optional[tuple[int, int, int, int, int, int]]:
    if isinstance(elem, DetectedElement):
        x, y, w, h = elem.x, elem.y, elem.width, elem.height
    else:
        x = int(elem.get("x") or 0)
        y = int(elem.get("y") or 0)
        w = int(elem.get("width") or 0)
        h = int(elem.get("height") or 0)
    if w < 4 or h < 4:
        return None
    return x, y, x + w, y + h, x + w // 2, y + h // 2


def _window_area(scope: Optional[dict]) -> int:
    if not scope:
        return 0
    rect = scope.get("client") or scope.get("visual") or {}
    rw = int(rect.get("w", rect.get("width", 0)) or 0)
    rh = int(rect.get("h", rect.get("height", 0)) or 0)
    return max(0, rw * rh)


def _split_by_gap(
    items: list[tuple[int, int, int, int, int, int, ElementLike]],
    gap_thresh: int,
    axis: int,
) -> list[list[tuple[int, int, int, int, int, int, ElementLike]]]:
    if not items:
        return []
    ordered = sorted(items, key=lambda t: t[axis])
    clusters: list[list] = [[ordered[0]]]
    for item in ordered[1:]:
        prev = clusters[-1][-1][axis]
        if item[axis] - prev > gap_thresh:
            clusters.append([item])
        else:
            clusters[-1].append(item)
    return clusters


def infer_content_region(
    elements: list[ElementLike],
    *,
    scope: Optional[dict] = None,
    min_elements: int = 6,
) -> Optional[dict[str, int]]:
    """Tight bbox around the dominant spatial cluster of controls."""
    window_area = _window_area(scope)
    items: list[tuple[int, int, int, int, int, int, ElementLike]] = []
    for elem in elements:
        box = _elem_box(elem)
        if not box:
            continue
        x1, y1, x2, y2, cx, cy = box
        if window_area and (x2 - x1) * (y2 - y1) > window_area * _MAX_AREA_RATIO:
            continue
        role = (
            elem.role if isinstance(elem, DetectedElement) else (elem.get("role") or "")
        ).strip()
        if role in _SKIP_ROLES:
            aid = (
                elem.automation_id
                if isinstance(elem, DetectedElement)
                else (elem.get("automation_id") or "")
            ).strip()
            name = (
                elem.name if isinstance(elem, DetectedElement) else (elem.get("name") or "")
            ).strip()
            if not aid and not name:
                continue
        items.append((cx, cy, x1, y1, x2, y2, elem))

    if len(items) < min_elements:
        return None

    widths = [it[4] - it[2] for it in items]
    heights = [it[5] - it[3] for it in items]
    median_w = sorted(widths)[len(widths) // 2]
    median_h = sorted(heights)[len(heights) // 2]
    wide_thresh = max(120, int(median_w * 2.2))
    normal = [it for it in items if (it[4] - it[2]) < wide_thresh]
    if len(normal) < min_elements:
        normal = items
    items = normal

    widths = [it[4] - it[2] for it in items]
    median_w = sorted(widths)[len(widths) // 2]
    median_h = sorted(heights)[len(heights) // 2]
    gap_x = max(48, int(median_w * 2.5))
    gap_y = max(40, int(median_h * 0.55))

    x_clusters = _split_by_gap(items, gap_x, axis=0)
    dominant = max(x_clusters, key=len)
    if len(dominant) < max(4, min_elements // 2):
        return None

    y_clusters = _split_by_gap(dominant, gap_y, axis=1)
    if len(y_clusters) > 1:
        y_dom = max(y_clusters, key=len)
        if len(y_dom) >= max(4, len(dominant) // 2):
            dominant = y_dom

    pad = max(12, int(median_w * 0.35))
    x1 = min(it[2] for it in dominant) - pad
    y1 = min(it[3] for it in dominant) - pad
    x2 = max(it[4] for it in dominant) + pad
    y2 = max(it[5] for it in dominant) + pad

    if scope:
        wr = scope.get("client") or scope.get("visual")
        if wr:
            rx = int(wr.get("x", 0))
            ry = int(wr.get("y", 0))
            rw = int(wr.get("w", wr.get("width", 0)) or 0)
            rh = int(wr.get("h", wr.get("height", 0)) or 0)
            x1 = max(rx, x1)
            y1 = max(ry, y1)
            x2 = min(rx + rw, x2)
            y2 = min(ry + rh, y2)

    if x2 <= x1 or y2 <= y1:
        return None
    return {"x": x1, "y": y1, "w": x2 - x1, "h": y2 - y1}


def element_in_content_region(
    elem: ElementLike,
    region: dict[str, int],
    *,
    window_title: Optional[str] = None,
    margin: int = 4,
) -> bool:
    from detection.element_coords import element_center_in_rect, to_screen_coords

    box = _elem_box(elem)
    if not box:
        return False
    x1, y1, x2, y2, _cx, _cy = box
    ew, eh = x2 - x1, y2 - y1
    rw = int(region.get("w", 0) or 0)
    rh = int(region.get("h", 0) or 0)

    if isinstance(elem, DetectedElement):
        raw = {"x": x1, "y": y1, "width": ew, "height": eh}
    else:
        raw = {"x": x1, "y": y1, "width": ew, "height": eh}
    normalized = to_screen_coords(raw, window_title)
    if not element_center_in_rect(normalized, region, margin=margin):
        return False

    # Wide strips that start left of the learned band (e.g. collapsed nav) are outliers.
    if rw > 0 and ew > max(int(rw * 0.45), 100):
        if x1 < int(region["x"]) + max(16, int(rw * 0.06)):
            return False
    if rh > 0 and eh < max(48, int(rh * 0.2)) and ew > int(rw * 0.55):
        return False
    return True


def _cache_key(scope: dict) -> str:
    title = (scope.get("window_title") or "").strip().lower()
    rect = scope.get("client") or scope.get("visual") or {}
    return f"{title}|{rect.get('x')}|{rect.get('y')}|{rect.get('w', rect.get('width'))}"


def _merge_region(prev: dict[str, int], new: dict[str, int]) -> dict[str, int]:
    x1 = min(prev["x"], new["x"])
    y1 = min(prev["y"], new["y"])
    x2 = max(prev["x"] + prev["w"], new["x"] + new["w"])
    y2 = max(prev["y"] + prev["h"], new["y"] + new["h"])
    return {"x": x1, "y": y1, "w": x2 - x1, "h": y2 - y1}


def remember_content_region(scope: dict, region: dict[str, int]) -> dict[str, int]:
    """Session cache: union with prior region for the same window (stable content band)."""
    key = _cache_key(scope)
    now = time.monotonic()
    hit = _CONTENT_CACHE.get(key)
    if hit and now - hit[0] < _CACHE_TTL:
        merged = _merge_region(hit[1], region)
    else:
        merged = dict(region)
    _CONTENT_CACHE[key] = (now, merged)
    return merged


def get_cached_content_region(scope: dict) -> Optional[dict[str, int]]:
    key = _cache_key(scope)
    hit = _CONTENT_CACHE.get(key)
    if not hit or time.monotonic() - hit[0] > _CACHE_TTL:
        return None
    return dict(hit[1])


def invalidate_content_region_cache(window_title: Optional[str] = None) -> int:
    if not window_title:
        n = len(_CONTENT_CACHE)
        _CONTENT_CACHE.clear()
        return n
    prefix = window_title.strip().lower()
    keys = [k for k in _CONTENT_CACHE if k.startswith(f"{prefix}|")]
    for k in keys:
        del _CONTENT_CACHE[k]
    return len(keys)


def resolve_content_walk_root(window_wrapper) -> Optional[object]:
    """Shallow pick widest Pane/Document child as walk root (Electron/main content)."""
    if window_wrapper is None:
        return None
    try:
        from detection.backends.uia_backend import _pywinauto_to_element

        best = None
        best_w = 0
        for child in window_wrapper.children() or []:
            det = _pywinauto_to_element(child)
            if not det:
                continue
            role = (det.role or "").strip().lower()
            if role not in ("pane", "document", "group"):
                continue
            w = int(det.width or 0)
            if w < 120 or w <= best_w:
                continue
            best_w = w
            best = child
        return best
    except Exception:
        return None


def filter_by_content_cluster(
    elements: list[DetectedElement],
    scope: dict,
    *,
    min_elements: int = 6,
    enabled: bool = True,
) -> tuple[list[DetectedElement], int, Optional[dict[str, int]]]:
    """Drop spatial outliers outside the dominant control cluster."""
    if not enabled or len(elements) < min_elements:
        return elements, 0, get_cached_content_region(scope)

    region = infer_content_region(elements, scope=scope, min_elements=min_elements)
    if region:
        region = remember_content_region(scope, region)
    else:
        region = get_cached_content_region(scope)
    if not region:
        return elements, 0, None

    window_title = scope.get("window_title")
    kept: list[DetectedElement] = []
    removed = 0
    for elem in elements:
        if element_in_content_region(elem, region, window_title=window_title):
            kept.append(elem)
        else:
            removed += 1

    if removed > len(elements) * _MAX_REMOVED_RATIO:
        return elements, 0, region

    return kept, removed, region

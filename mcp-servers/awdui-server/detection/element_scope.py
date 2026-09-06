"""Scope list_elements results to the target window (PID + client rect)."""
from __future__ import annotations

from typing import Optional

from detection.element_model import DetectedElement


def resolve_window_scope(window_title: Optional[str] = None) -> Optional[dict]:
    """Visual client rect and allowed process IDs for *window_title*."""
    from tools.target_window import get_target
    from tools.windows import do_list_windows, find_matching_window, resolve_window_visual_rect

    title = (window_title or get_target() or "").strip()
    if not title:
        return None

    title_lower = title.lower()
    windows = do_list_windows()
    candidates = [
        w for w in windows
        if title_lower in (w.get("title") or "").lower()
    ]
    if not candidates:
        match = find_matching_window(title, windows)
        if match.get("window"):
            candidates = [match["window"]]

    process_ids: set[int] = set()
    best = None
    for win in candidates:
        pid = int(win.get("pid") or 0)
        if pid:
            process_ids.add(pid)
        if best is None:
            best = win
        else:
            area = max(0, win.get("width", 0)) * max(0, win.get("height", 0))
            best_area = max(0, best.get("width", 0)) * max(0, best.get("height", 0))
            if area > best_area:
                best = win

    try:
        from tools.framework_detect import _get_hwnd_for_window
        from detection.app_identity import _resolve_uwp_core_from_shell

        hwnd = int(_get_hwnd_for_window(title) or 0)
        if hwnd:
            _, _, core_pid = _resolve_uwp_core_from_shell(hwnd)
            if core_pid:
                process_ids.add(core_pid)
    except Exception:
        pass

    visual = resolve_window_visual_rect(title)
    client = None
    if best:
        cx = int(best.get("client_x", best.get("x", 0)) or 0)
        cy = int(best.get("client_y", best.get("y", 0)) or 0)
        cw = int(best.get("client_width", best.get("width", 0)) or 0)
        ch = int(best.get("client_height", best.get("height", 0)) or 0)
        if cw > 0 and ch > 0:
            client = {"x": cx, "y": cy, "w": cw, "h": ch}

    return {
        "window_title": title,
        "visual": visual,
        "client": client,
        "process_ids": process_ids,
    }


def element_in_window_scope(
    elem: DetectedElement | dict,
    scope: dict,
    *,
    margin: int = 2,
) -> bool:
    """True when element belongs to scoped window (PID + center inside client/visual rect)."""
    if isinstance(elem, DetectedElement):
        data = {
            "x": elem.x,
            "y": elem.y,
            "width": elem.width,
            "height": elem.height,
            "process_id": elem.process_id,
            "framework_id": elem.framework_id,
        }
    else:
        data = elem

    pids = scope.get("process_ids") or set()
    pid = int(data.get("process_id") or 0)
    if pids and pid and pid not in pids:
        fw = (data.get("framework_id") or "").upper()
        # UWP: CoreWindow (XAML) PID may differ from ApplicationFrameHost HWND PID.
        if fw != "XAML":
            return False

    rect = scope.get("client") or scope.get("visual")
    if not rect:
        return True

    from detection.element_coords import element_center_in_rect, to_screen_coords

    normalized = to_screen_coords(
        {
            "x": int(data.get("x", 0) or 0),
            "y": int(data.get("y", 0) or 0),
            "width": int(data.get("width") or data.get("w") or 0),
            "height": int(data.get("height") or data.get("h") or 0),
        },
        scope.get("window_title"),
    )
    return element_center_in_rect(normalized, rect, margin=margin)


def filter_elements_to_scope(
    elements: list[DetectedElement],
    window_title: Optional[str] = None,
    *,
    adaptive_cluster: bool = True,
) -> tuple[list[DetectedElement], int, int, Optional[dict]]:
    """Filter by window scope, then optional dominant spatial cluster.

    Returns (kept, scoped_out_count, cluster_out_count, content_region).
    """
    scope = resolve_window_scope(window_title)
    if not scope:
        return elements, 0, 0, None

    kept: list[DetectedElement] = []
    scoped_out = 0
    for elem in elements:
        if element_in_window_scope(elem, scope):
            kept.append(elem)
        else:
            scoped_out += 1

    from detection.spatial_cluster import filter_by_content_cluster

    kept, cluster_out, region = filter_by_content_cluster(
        kept, scope, enabled=adaptive_cluster,
    )
    return kept, scoped_out, cluster_out, region

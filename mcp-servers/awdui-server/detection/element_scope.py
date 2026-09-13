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
        "allow_renderer_pid": _framework_allows_renderer_pid(title),
    }


def _framework_allows_renderer_pid(window_title: Optional[str]) -> bool:
    """Electron/WebView2 UIA nodes often report renderer PID != shell HWND PID."""
    try:
        from tools.framework_detect import do_detect_framework

        fw = do_detect_framework(window_title).get("framework", "")
        if fw in ("electron", "chromium_browser", "unknown"):
            try:
                from tools.window_classify import classify_window

                info = classify_window(window_title=window_title)
                proc = (info.get("process") or "").lower()
                cls = (info.get("class_name") or "")
                if proc == "ms-teams.exe" or cls == "TeamsWebView":
                    return True
            except Exception:
                pass
        return fw in ("electron", "chromium_browser")
    except Exception:
        return False


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
        if fw == "XAML" or scope.get("allow_renderer_pid"):
            pass
        else:
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
    rw = int(rect.get("w") or rect.get("width") or 0)
    rh = int(rect.get("h") or rect.get("height") or 0)
    compact = rw > 0 and rh > 0 and (rw * rh) < 280_000
    margin = 0 if compact else 2
    if compact:
        ex = int(normalized.get("x", 0))
        ey = int(normalized.get("y", 0))
        ew = int(normalized.get("width", 0) or 0)
        eh = int(normalized.get("height", 0) or 0)
        if ew <= 0 or eh <= 0:
            return element_center_in_rect(normalized, rect, margin=margin)
        rx = int(rect.get("x", 0))
        ry = int(rect.get("y", 0))
        return (
            ex + ew > rx + margin
            and ey + eh > ry + margin
            and ex < rx + rw - margin
            and ey < ry + rh - margin
        )
    return element_center_in_rect(normalized, rect, margin=margin)


def _drop_electron_compact_tree_rows(
    elements: list[DetectedElement],
    scope: dict,
) -> list[DetectedElement]:
    """Drop ultra-compact TreeItem rows common in foreign file-tree UIA leak."""
    out: list[DetectedElement] = []
    for elem in elements:
        role = (elem.role or "").strip()
        aid = (elem.automation_id or "").strip()
        h = int(elem.height or 0)
        if role == "TreeItem" and aid.startswith("list_id_"):
            continue
        if scope.get("allow_renderer_pid") and role == "TreeItem" and 0 < h < 28:
            continue
        out.append(elem)
    return out


def filter_elements_to_scope(
    elements: list[DetectedElement],
    window_title: Optional[str] = None,
    *,
    adaptive_cluster: bool = True,
    include_offscreen: bool = False,
) -> tuple[list[DetectedElement], int, int, Optional[dict]]:
    """Filter by window scope, then optional dominant spatial cluster.

    Returns (kept, scoped_out_count, cluster_out_count, content_region).
    """
    scope = resolve_window_scope(window_title)
    if not scope:
        return elements, 0, 0, None

    kept: list[DetectedElement] = []
    scoped_out = 0
    client = scope.get("client") or scope.get("visual")
    sidebar_max_x: Optional[int] = None
    if include_offscreen and client:
        sidebar_max_x = int(client["x"]) + int(client.get("w", client.get("width", 0)) * 0.45)

    for elem in elements:
        role = (elem.role or "").strip()
        if include_offscreen and sidebar_max_x is not None and role == "TreeItem":
            from detection.element_coords import to_screen_coords

            normalized = to_screen_coords(
                {
                    "x": int(elem.x or 0),
                    "y": int(elem.y or 0),
                    "width": int(elem.width or 0),
                    "height": int(elem.height or 0),
                },
                scope.get("window_title"),
            )
            center_x = int(normalized.get("x", 0)) + int(normalized.get("width", 0) or 0) // 2
            if center_x <= sidebar_max_x:
                kept.append(elem)
                continue
        if element_in_window_scope(elem, scope):
            kept.append(elem)
        else:
            scoped_out += 1

    kept = _drop_electron_compact_tree_rows(kept, scope)

    from detection.spatial_cluster import filter_by_content_cluster

    kept, cluster_out, region = filter_by_content_cluster(
        kept, scope, enabled=adaptive_cluster,
    )
    return kept, scoped_out, cluster_out, region


def filter_dict_elements_to_scope(
    elements: list[dict],
    window_title: Optional[str] = None,
    *,
    automation_id: Optional[str] = None,
) -> tuple[list[dict], dict]:
    """Filter find/wait results to the target window (client rect + optional automation_id)."""
    meta: dict = {
        "scope_mode": "no_target",
        "rejected_foreign": 0,
        "target_hwnd": None,
    }
    if not elements:
        return [], meta

    scope = resolve_window_scope(window_title)
    if not scope:
        return list(elements), meta

    meta["scope_mode"] = "client_rect"
    try:
        from tools.framework_detect import _get_hwnd_for_window

        hwnd = int(_get_hwnd_for_window(scope.get("window_title") or window_title or "") or 0)
        if hwnd:
            meta["target_hwnd"] = hwnd
    except Exception:
        pass

    aid = (automation_id or "").strip()
    allowed_aids: set[str] = set()
    if aid:
        from detection.automation_id_aliases import alias_candidates

        allowed_aids = set(alias_candidates(aid))
    kept: list[dict] = []
    rejected = 0
    for elem in elements:
        if not element_in_window_scope(elem, scope):
            rejected += 1
            continue
        if allowed_aids:
            elem_aid = (elem.get("automation_id") or "").strip()
            if elem_aid not in allowed_aids:
                rejected += 1
                continue
        kept.append(elem)
    meta["rejected_foreign"] = rejected
    return kept, meta


def scope_metadata_for_find(
    window_title: Optional[str] = None,
    *,
    rejected_foreign: int = 0,
) -> dict:
    """Build scope fields to attach to find/wait responses."""
    scope = resolve_window_scope(window_title)
    meta: dict = {
        "scope_mode": "client_rect" if scope else "no_target",
        "rejected_foreign": rejected_foreign,
        "target_hwnd": None,
    }
    if scope:
        try:
            from tools.framework_detect import _get_hwnd_for_window

            hwnd = int(_get_hwnd_for_window(scope.get("window_title") or window_title or "") or 0)
            if hwnd:
                meta["target_hwnd"] = hwnd
        except Exception:
            pass
    return meta


def _bbox_contains(outer: dict, inner: dict, margin: int = 2) -> bool:
    ox, oy = int(outer.get("x") or 0), int(outer.get("y") or 0)
    ow, oh = int(outer.get("width") or 0), int(outer.get("height") or 0)
    if ow <= 0 or oh <= 0:
        return True
    ix, iy = int(inner.get("x") or 0), int(inner.get("y") or 0)
    iw, ih = int(inner.get("width") or 0), int(inner.get("height") or 0)
    if iw <= 0 or ih <= 0:
        cx, cy = ix, iy
    else:
        cx, cy = ix + iw // 2, iy + ih // 2
    return (
        ox - margin <= cx <= ox + ow + margin
        and oy - margin <= cy <= oy + oh + margin
    )


def filter_elements_by_ancestor(
    elements: list[DetectedElement],
    ancestor_automation_id: str,
) -> tuple[list[DetectedElement], dict]:
    """Keep only elements whose center lies inside the ancestor bbox."""
    aid = (ancestor_automation_id or "").strip()
    meta = {"ancestor_automation_id": aid, "ancestor_found": False, "filtered_out": 0}
    if not aid:
        return elements, meta
    ancestor = None
    for elem in elements:
        if (elem.automation_id or "").strip() == aid:
            ancestor = elem
            break
    if ancestor is None:
        return [], {**meta, "error": f"ancestor not in tree: {aid}"}
    meta["ancestor_found"] = True
    outer = {"x": ancestor.x, "y": ancestor.y, "width": ancestor.width, "height": ancestor.height}
    kept: list[DetectedElement] = []
    for elem in elements:
        inner = {"x": elem.x, "y": elem.y, "width": elem.width, "height": elem.height}
        if _bbox_contains(outer, inner):
            kept.append(elem)
        else:
            meta["filtered_out"] += 1
    return kept, meta

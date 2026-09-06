"""ASCII 'eye' view of the target window UI."""
from __future__ import annotations

import json
import sys
from typing import Any, Optional


def _bbox_from_elements(elements: list[dict[str, Any]]) -> tuple[int, int, int, int]:
    xs = [int(e.get("x", 0)) for e in elements]
    ys = [int(e.get("y", 0)) for e in elements]
    x2 = [int(e.get("x", 0)) + int(e.get("width", 0)) for e in elements]
    y2 = [int(e.get("y", 0)) + int(e.get("height", 0)) for e in elements]
    if not xs:
        return 0, 0, 1, 1
    pad = 8
    ox, oy = min(xs) - pad, min(ys) - pad
    ww = max(x2) - ox + pad
    wh = max(y2) - oy + pad
    return ox, oy, max(ww, 1), max(wh, 1)


def _count_inside(
    elements: list[dict[str, Any]],
    origin_x: int,
    origin_y: int,
    win_w: int,
    win_h: int,
) -> int:
    n = 0
    for elem in elements:
        w = int(elem.get("width") or 0)
        h = int(elem.get("height") or 0)
        if w <= 0 or h <= 0:
            continue
        x = int(elem.get("x") or 0)
        y = int(elem.get("y") or 0)
        cx = x + w // 2
        cy = y + h // 2
        if origin_x <= cx <= origin_x + win_w and origin_y <= cy <= origin_y + win_h:
            n += 1
    return n


def do_ascii_ui_view(
    window_title: Optional[str] = None,
    window_handle: Optional[int] = None,
    width: int = 100,
    height: int = 52,
    max_depth: Optional[int] = None,
    role: Optional[str] = None,
    min_pixels: int = 6,
    include_legend: bool = True,
    include_focus: bool = True,
    detail: str = "basic",
    unicode_box: bool = True,
    include_keys: bool = False,
    include_tab_index: bool = False,
    include_elements: bool = True,
    occlusion_prune: bool = True,
    ocr: bool = False,
    preserve_aspect: bool = True,
    layout_mode: str = "legible",
    use_colors: bool = False,
    include_offscreen: bool = False,
    tree_mode: str = "control",
) -> dict[str, Any]:
    """List UIA elements and render a simplified ASCII map of the window."""
    if sys.platform != "win32":
        return {"success": False, "error": "ascii_ui_view is Windows-only"}

    from detection.ascii_ui_render import render_ascii_ui, select_elements_for_ascii_render
    from detection.tree_depth import ASCII_UI_DEFAULT_MAX_DEPTH, resolve_list_depth
    from tools.params import resolve_window_title
    from tools.target_window import get_target
    from tools.ui_automation import do_get_focused_element, do_list_elements
    from tools.windows import resolve_window_handle, resolve_window_visual_rect

    wt = resolve_window_title(window_title, "") or (get_target() or "").strip() or None
    hwnd = int(window_handle or 0) or (resolve_window_handle(wt or "") or 0)

    requested_depth, effective_depth, fw_depth = resolve_list_depth(
        max_depth if max_depth is not None else ASCII_UI_DEFAULT_MAX_DEPTH,
        role=role,
        window_title=wt,
    )

    listing = do_list_elements(
        window_title=wt,
        window_handle=hwnd or None,
        max_depth=effective_depth,
        role=role or None,
        include_offscreen=bool(include_offscreen),
        tree_mode=(tree_mode or "control"),
    )
    elements = list(listing.get("elements") or [])
    if not elements:
        return {
            "success": False,
            "error": listing.get("error") or "no elements in window",
            "backend_used": listing.get("backend_used", ""),
        }

    visual = resolve_window_visual_rect(wt) if wt else None
    if visual:
        origin_x = int(visual.get("x", 0))
        origin_y = int(visual.get("y", 0))
        win_w = int(visual.get("width", 0))
        win_h = int(visual.get("height", 0))
        frame_title = visual.get("title") or wt or ""
        inside = _count_inside(elements, origin_x, origin_y, win_w, win_h)
        if inside < max(1, len(elements) // 5):
            origin_x, origin_y, win_w, win_h = _bbox_from_elements(elements)
    else:
        origin_x, origin_y, win_w, win_h = _bbox_from_elements(elements)
        frame_title = wt or "foreground"

    basic_only = (detail or "basic").lower() != "full"

    ocr_enriched = 0
    ocr_words = 0
    if ocr:
        try:
            from detection.ascii_ui_ocr import enrich_elements_with_ocr

            elements, ocr_words, ocr_enriched = enrich_elements_with_ocr(
                elements,
                origin_x,
                origin_y,
                win_w,
                win_h,
                window_title=wt,
            )
        except Exception:
            pass

    filtered = select_elements_for_ascii_render(
        elements,
        origin_x,
        origin_y,
        win_w,
        win_h,
        min_pixels=max(4, int(min_pixels or 6)),
        basic_only=basic_only,
        occlusion_prune=occlusion_prune,
    )
    if not filtered and elements:
        origin_x, origin_y, win_w, win_h = _bbox_from_elements(elements)
        filtered = select_elements_for_ascii_render(
            elements,
            origin_x,
            origin_y,
            win_w,
            win_h,
            min_pixels=4,
            max_area_ratio=0.98,
            basic_only=basic_only,
            occlusion_prune=occlusion_prune,
        )

    focused_elem: Optional[dict[str, Any]] = None
    if include_focus:
        try:
            foc = do_get_focused_element()
            if foc.get("found"):
                focused_elem = foc.get("element") or foc.get("properties") or {}
        except Exception:
            focused_elem = None

    layout_ox, layout_oy, layout_ww, layout_wh = _bbox_from_elements(filtered)

    rendered = render_ascii_ui(
        filtered,
        layout_ox,
        layout_oy,
        layout_ww,
        layout_wh,
        cols=width,
        height=height,
        title=frame_title,
        focused=focused_elem,
        unicode_box=unicode_box,
        include_keys=include_keys,
        include_tab_index=include_tab_index,
        preserve_aspect=preserve_aspect,
        layout_mode=layout_mode,
        use_colors=use_colors,
    )

    ascii_out = rendered["ascii"]
    if include_legend:
        ascii_out = f"{ascii_out}\n\n{rendered['legend']}"

    result: dict[str, Any] = {
        "success": True,
        "ascii": ascii_out,
        "window_title": frame_title,
        "element_count": len(elements),
        "rendered_count": len(filtered),
        "cols": rendered["cols"],
        "rows": rendered["rows"],
        "origin": {"x": origin_x, "y": origin_y, "width": win_w, "height": win_h},
        "viewport": rendered.get("viewport"),
        "backend_used": listing.get("backend_used", ""),
        "list_ms": listing.get("list_ms"),
        "ocr_enriched": ocr_enriched,
        "ocr_words": ocr_words,
        "include_offscreen": bool(include_offscreen),
        "tree_mode": tree_mode or "control",
        "max_depth_requested": requested_depth,
        "max_depth_effective": effective_depth,
        "framework_depth": fw_depth or None,
    }
    if include_elements:
        result["elements"] = rendered.get("elements") or []
    return result


def register(server) -> int:
    from tools.params import resolve_window_title as _wt
    from tools.safety import ActionTimeoutError, with_timeout

    @server.tool()
    def ascii_ui_view(
        window_title: str = "",
        title: str = "",
        window_handle: int = 0,
        width: int = 100,
        height: int = 52,
        max_depth: int = 0,
        role: str = "",
        min_pixels: int = 6,
        include_legend: bool = True,
        include_focus: bool = True,
        detail: str = "basic",
        unicode_box: bool = True,
        include_keys: bool = False,
        include_tab_index: bool = False,
        include_elements: bool = True,
        occlusion_prune: bool = True,
        ocr: bool = False,
        preserve_aspect: bool = True,
        layout_mode: str = "legible",
        use_colors: bool = False,
        include_offscreen: bool = False,
        tree_mode: str = "control",
    ) -> str:
        """Render the target window as a simplified ASCII map (UI 'eye' for agents).

        Walks the UIA tree and draws controls as labeled boxes in a character grid.
        Uses containment-tree leaf selection and sibling occlusion pruning to reduce overlap.
        preserve_aspect=true (default) maps pixel bboxes with char-aspect correction (layout_mode=proportional).
        layout_mode: proportional | legible | stretch.
        include_offscreen=true includes UIA nodes marked offscreen (collapsed panels, etc.).
        ocr=true runs RapidOCR on the window (and ROI crops) to name Image/Custom controls.
        use_colors=false (default) — plain ASCII boxes; true adds ANSI fills (terminal only).
        Each control gets a legend key (e1, e2, …) and optional tab-order badge (①②…).
        detail=basic (default) shows buttons, text/display, edits, combos only.
        """
        try:
            result = with_timeout(
                lambda: do_ascii_ui_view(
                    window_title=_wt(window_title, title) or None,
                    window_handle=window_handle or None,
                    width=width,
                    height=height,
                    max_depth=max_depth,
                    role=role or None,
                    min_pixels=min_pixels,
                    include_legend=include_legend,
                    include_focus=include_focus,
                    detail=detail,
                    unicode_box=unicode_box,
                    include_keys=include_keys,
                    include_tab_index=include_tab_index,
                    include_elements=include_elements,
                    occlusion_prune=occlusion_prune,
                    ocr=ocr,
                    preserve_aspect=preserve_aspect,
                    layout_mode=layout_mode,
                    use_colors=use_colors,
                    include_offscreen=include_offscreen,
                    tree_mode=tree_mode,
                ),
                timeout=25.0,
            )
        except ActionTimeoutError as exc:
            return f"ERROR: {exc}"
        if not result.get("success"):
            return result.get("error", "ascii_ui_view failed")
        meta = (
            f"window={result.get('window_title')} "
            f"rendered={result.get('rendered_count')}/{result.get('element_count')} "
            f"grid={result.get('cols')}x{result.get('rows')}"
        )
        if result.get("ocr_enriched"):
            meta += f" ocr_enriched={result.get('ocr_enriched')}"
        body = f"{meta}\n\n```\n{result.get('ascii', '')}\n```"
        elems = result.get("elements")
        if include_elements and elems:
            body += "\n\nelements:\n```json\n"
            body += json.dumps(elems, ensure_ascii=False, indent=2)
            body += "\n```"
        return body

    return 1

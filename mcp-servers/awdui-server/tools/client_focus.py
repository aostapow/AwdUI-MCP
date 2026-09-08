"""Ensure keyboard focus lands in the target app's primary client input area."""
from __future__ import annotations

import sys
from typing import Any, Optional

_CLIENT_INPUT_ROLES = frozenset({"document", "edit", "text", "textbox"})


def _is_client_input(elem: dict[str, Any]) -> bool:
    return (elem.get("role") or "").strip().lower() in _CLIENT_INPUT_ROLES


def _pick_largest_element(elements: list[dict[str, Any]]) -> dict[str, Any]:
    best = elements[0]
    best_area = -1
    for elem in elements:
        area = int(elem.get("width") or 0) * int(elem.get("height") or 0)
        if area > best_area:
            best_area = area
            best = elem
    return best


def _find_client_input_elements(
    window_title: Optional[str],
    automation_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    from tools.ui_automation import do_find_element

    if automation_id:
        found = do_find_element(
            automation_id=automation_id,
            window_title=window_title,
            include_offscreen=True,
            remember=False,
        )
        if found.get("found"):
            return [
                e for e in found.get("elements") or []
                if _is_client_input(e)
            ] or list(found.get("elements") or [])

    candidates: list[dict[str, Any]] = []
    for role in ("Document", "Edit"):
        found = do_find_element(
            role=role,
            window_title=window_title,
            include_offscreen=False,
            remember=False,
        )
        if found.get("found"):
            candidates.extend(found.get("elements") or [])
    return candidates


def ensure_client_focus(
    window_title: Optional[str] = None,
    automation_id: Optional[str] = None,
) -> dict[str, Any]:
    """Focus Document/Edit (or explicit automation_id) in the target window."""
    if sys.platform != "win32":
        return {"success": True, "method": "skipped_non_win32"}

    from tools.target_window import get_target
    from tools.ui_automation import do_get_focused_element

    wt = (window_title or get_target() or "").strip() or None

    focused = do_get_focused_element()
    if focused.get("found") and _is_client_input(focused.get("element") or {}):
        return {
            "success": True,
            "method": "already_focused",
            "element": focused["element"],
        }

    candidates = _find_client_input_elements(wt, automation_id=automation_id)
    if not candidates:
        return {
            "success": False,
            "error": "No client input control found in target window",
            "code": "no_client_input",
        }

    elem = _pick_largest_element(candidates)

    from detection.backends.uia_backend import get_uia_backend
    from detection.element_model import DetectedElement

    detected = DetectedElement(
        name=elem.get("name") or "",
        role=elem.get("role") or "",
        automation_id=elem.get("automation_id") or "",
    )
    focus_result = get_uia_backend().focus_element(detected, window_title=wt)
    if focus_result.get("success"):
        verify = do_get_focused_element()
        if verify.get("found") and _is_client_input(verify.get("element") or {}):
            return {
                "success": True,
                "method": "SetFocus",
                "element": elem,
            }

    from tools.ui_automation import _click_coords
    from tools.input_tools import do_click

    cx, cy = _click_coords(elem, wt)
    click_result = do_click(cx, cy, verify_visual=False)
    if not click_result.get("success", True) and click_result.get("error"):
        return {
            "success": False,
            "error": click_result.get("error", "bbox click failed"),
            "element": elem,
        }

    verify = do_get_focused_element()
    if verify.get("found") and _is_client_input(verify.get("element") or {}):
        return {
            "success": True,
            "method": "ClientInput_bbox_fallback",
            "element": elem,
            "clicked_at": {"x": cx, "y": cy},
        }

    return {
        "success": False,
        "error": "Client input focus not verified after SetFocus and bbox click",
        "element": elem,
        "focus_attempt": focus_result,
    }

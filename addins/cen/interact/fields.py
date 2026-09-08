"""Read/write COBIS fields with type-aware handling."""
from __future__ import annotations

from typing import Any, Optional

from detect.classifier import classify_element


def _resolve(automation_id: str, name: str, window_title: Optional[str]):
    from grid.resolve import resolve_grid

    aid = automation_id or name
    return resolve_grid(aid, name, window_title)


def read_field(
    automation_id: str = "",
    name: str = "",
    window_title: Optional[str] = None,
    use_clip_text: bool = True,
) -> dict[str, Any]:
    raw, element, scope = _resolve(automation_id, name, window_title)
    if not raw:
        return {"success": False, **scope}

    classified = classify_element(element)
    cen_type = classified.get("cen_type", "")

    from tools.control_items import _ControlView
    from detection.backends.uia_backend import _pywinauto_to_element

    det = _pywinauto_to_element(raw)
    data = det.to_dict() if det else element
    value = (data.get("value") or data.get("name") or "").strip()
    display = (data.get("name") or "").strip()

    if cen_type in ("cobis_masked_inbox", "cobis_masked_text") and use_clip_text:
        try:
            clip = getattr(raw, "ClipText", None)
            if clip is not None:
                value = str(clip).strip() or value
        except Exception:
            pass

    return {
        "success": True,
        "automation_id": data.get("automation_id") or automation_id or name,
        "cen_type": cen_type,
        "value": value,
        "display": display,
        "resolved_window_title": scope.get("resolved_title") or "",
    }


def set_field(
    automation_id: str = "",
    name: str = "",
    value: str = "",
    window_title: Optional[str] = None,
    clear_first: bool = True,
) -> dict[str, Any]:
    aid = (automation_id or name or "").strip()
    if not aid:
        return {"success": False, "error": "automation_id or name required"}

    classified_hint = classify_element({"automation_id": aid, "name": name or aid})
    cen_type = classified_hint.get("cen_type", "")

    from tools.ui_automation import do_click_element, do_set_element_value

    if clear_first:
        do_click_element(automation_id=aid, window_title=window_title or "")
    result = do_set_element_value(value, automation_id=aid, name=name or None, window_title=window_title or "")

    ok = isinstance(result, dict) and result.get("success", True)
    if isinstance(result, str):
        ok = "error" not in result.lower()

    return {
        "success": bool(ok),
        "automation_id": aid,
        "cen_type": cen_type,
        "value_set": value,
        "raw_result": result,
        "hint": "Tab out or click away to trigger Leave validation on msk*/txt* fields",
    }

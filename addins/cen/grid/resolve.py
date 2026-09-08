"""Resolve COBIS grid controls to UIA raw wrappers."""
from __future__ import annotations

import sys
from typing import Any, Optional


def resolve_grid(
    automation_id: str = "",
    name: str = "",
    window_title: Optional[str] = None,
) -> tuple[Optional[object], dict[str, Any], dict[str, Any]]:
    """Return (raw_uia_wrapper, element_dict, scope)."""
    if sys.platform != "win32":
        return None, {}, {"error": "Windows-only"}

    aid = (automation_id or "").strip()
    ctrl_name = (name or "").strip()
    if not aid and not ctrl_name:
        return None, {}, {"error": "automation_id or name is required"}

    from tools.window_scope import resolve_window_scope

    scope = resolve_window_scope(window_title)
    title = scope.get("resolved_title") or window_title

    from detection.backends.uia_backend import (
        _find_raw_by_automation_id,
        _find_window,
        _get_desktop,
        _pywinauto_to_element,
    )

    desktop = _get_desktop()
    window = _find_window(desktop, title)
    if not window:
        return None, {}, {**scope, "error": f"Window not found: {title or '(target)'}"}

    raw = None
    if aid:
        raw = _find_raw_by_automation_id(window, aid)
    if raw is None and ctrl_name:
        raw = _find_raw_by_automation_id(window, ctrl_name)
    if raw is None and ctrl_name:
        try:
            raw = window.child_window(title=ctrl_name, control_type="DataGrid").wrapper_object()
        except Exception:
            raw = None
    if raw is None and ctrl_name:
        try:
            raw = window.child_window(title=ctrl_name).wrapper_object()
        except Exception:
            raw = None

    if not raw:
        label = aid or ctrl_name
        return None, {}, {**scope, "error": f"Grid control not found: {label}"}

    det = _pywinauto_to_element(raw)
    data = det.to_dict() if det else {"automation_id": aid or ctrl_name, "name": ctrl_name}
    return raw, data, scope

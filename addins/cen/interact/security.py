"""Toolbar security metadata (cmdBoton.Tag transaction codes)."""
from __future__ import annotations

from typing import Any, Optional

from toolbar import list_cobis_toolbar


def read_toolbar_security(window_title: Optional[str] = None) -> dict[str, Any]:
    """List toolbar buttons with Tag hints from forms_index when profile matches."""
    from detect.forms import match_form_profile
    from tools.ui_automation import do_get_element_properties

    toolbar = list_cobis_toolbar(window_title)
    profile = match_form_profile(toolbar.get("resolved_window_title") or window_title or "")

    enriched = []
    profile_map = profile.get("toolbar_map") or {}
    for btn in toolbar.get("buttons") or []:
        idx = str(btn.get("index", ""))
        prof = profile_map.get(idx, {})
        tag_hint = prof.get("tag")
        entry = {**btn, "transaction_tag_hint": tag_hint, "handler_hint": prof.get("handler")}
        aid = btn.get("automation_id") or ""
        if aid:
            try:
                props = do_get_element_properties(
                    automation_id=aid,
                    window_title=window_title or toolbar.get("resolved_window_title") or "",
                )
                if isinstance(props, dict):
                    entry["uia_properties"] = {
                        k: props.get(k)
                        for k in ("enabled", "visible", "name", "value")
                        if k in props
                    }
            except Exception:
                pass
        if prof.get("admin_only"):
            entry["admin_only"] = True
        enriched.append(entry)

    return {
        "success": toolbar.get("success", True),
        "form_profile": profile,
        "buttons": enriched,
        "resolved_window_title": toolbar.get("resolved_window_title") or window_title or "",
        "note": "Tag is WinForms property; UIA may not expose it — use forms_index hints",
    }

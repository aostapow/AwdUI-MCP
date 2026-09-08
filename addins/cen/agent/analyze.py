"""One-shot form analysis for agents."""
from __future__ import annotations

from typing import Any, Optional

from agent.suggest import suggest_next_action
from detect.form_context import build_form_context
from detect.forms import match_form_profile
from detect.modals import detect_modal


def analyze_form(window_title: Optional[str] = None, max_depth: int = 6) -> dict[str, Any]:
    """Combined snapshot: profile, context, modals, controls summary, suggestions."""
    from catalog import list_classified_controls
    from detect.forms_catalog import get_form_profile
    from toolbar import list_cobis_toolbar

    catalog = list_classified_controls(window_title, max_depth=max_depth)
    if not catalog.get("success"):
        return catalog

    title = catalog.get("resolved_window_title") or window_title or ""
    elems = catalog.get("controls") or []
    profile = match_form_profile(title, elems)
    modal = detect_modal(title)
    context = build_form_context(title, elems)
    toolbar_live = list_cobis_toolbar(title)
    suggestions = suggest_next_action(title)

    static_profile = None
    if profile.get("matched"):
        static_profile = get_form_profile(profile["form_id"])

    by_type = catalog.get("by_cen_type") or {}
    return {
        "success": True,
        "window_title": title,
        "form_profile": profile,
        "static_profile": (static_profile or {}).get("form"),
        "modal": modal,
        "context": context,
        "control_summary": {
            "total": catalog.get("total_elements"),
            "classified": catalog.get("classified_count"),
            "by_cen_type": by_type,
        },
        "toolbar_live": toolbar_live,
        "suggestions": suggestions.get("suggestions", []),
        "warnings": suggestions.get("warnings", []),
        "recommended_first_tools": [
            t["tool"]
            for t in (suggestions.get("suggestions") or [])[:3]
        ],
    }

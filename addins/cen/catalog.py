"""List and classify all controls on active CEN form."""
from __future__ import annotations

import json
from typing import Any, Optional

from detect.classifier import classify_element
from detect.form_context import build_form_context


def list_classified_controls(
    window_title: Optional[str] = None,
    max_depth: int = 8,
) -> dict[str, Any]:
    from tools.ui_automation import do_list_elements

    listed = do_list_elements(window_title=window_title or "", max_depth=max_depth)
    if isinstance(listed, str):
        listed = json.loads(listed)

    elements = listed.get("elements") or []
    classified = []
    by_type: dict[str, int] = {}

    for el in elements:
        cen = classify_element(el)
        ctype = cen.get("cen_type", "unknown")
        by_type[ctype] = by_type.get(ctype, 0) + 1
        if ctype != "unknown" or (el.get("name") or "").startswith(("txt", "msk", "grd", "cmd", "lbl", "cbo", "opt")):
            classified.append({**el, "cen": cen})

    ctx = build_form_context(
        window_title=listed.get("resolved_window_title") or window_title,
        elements=elements,
    )

    return {
        "success": True,
        "resolved_window_title": listed.get("resolved_window_title") or window_title or "",
        "total_elements": len(elements),
        "classified_count": len(classified),
        "by_cen_type": by_type,
        "controls": classified[:200],
        "context": ctx,
    }


def find_controls(
    prefix: str = "",
    cen_type: str = "",
    window_title: Optional[str] = None,
    max_depth: int = 8,
) -> dict[str, Any]:
    """Filter classified controls by name prefix or cen_type."""
    catalog = list_classified_controls(window_title, max_depth=max_depth)
    if not catalog.get("success"):
        return catalog

    matches = []
    for ctrl in catalog.get("controls") or []:
        name = (ctrl.get("name") or ctrl.get("automation_id") or "").strip()
        ctype = (ctrl.get("cen") or {}).get("cen_type", "")
        if prefix and not name.lower().startswith(prefix.lower()):
            continue
        if cen_type and ctype != cen_type:
            continue
        matches.append(ctrl)

    return {
        "success": True,
        "resolved_window_title": catalog.get("resolved_window_title", ""),
        "filter": {"prefix": prefix, "cen_type": cen_type},
        "count": len(matches),
        "controls": matches[:100],
    }

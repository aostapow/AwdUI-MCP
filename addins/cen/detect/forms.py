"""Match active window against known form profiles from static analysis."""
from __future__ import annotations

from typing import Any, Optional

from detect.forms_catalog import _load_catalog


def match_form_profile(
    window_title: str = "",
    elements: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    title = (window_title or "").lower()
    elems = elements or []
    names = {
        (el.get("name") or el.get("automation_id") or "").lower()
        for el in elems
    }

    best: Optional[dict[str, Any]] = None
    best_score = 0.0

    for form in _load_catalog().get("forms") or []:
        score = 0.0
        fid = (form.get("id") or "").lower()
        if fid and fid in title:
            score += 0.65
        for hint in form.get("title_hints", []):
            if hint.lower() in title:
                score += 0.25
        key_fields = form.get("key_fields") or []
        field_hits = sum(1 for f in key_fields if f.lower() in names)
        if key_fields:
            score += min(field_hits / len(key_fields), 1.0) * 0.45
        grids = form.get("grids") or []
        grid_hits = sum(1 for g in grids if g.lower() in names)
        if grids and grid_hits:
            score += min(grid_hits / len(grids), 1.0) * 0.25
        # Strong match: 2+ grids or 3+ fields visible
        if field_hits >= 3 or grid_hits >= 2:
            score += 0.15
        if score > best_score:
            best_score = score
            best = form

    if not best or best_score < 0.38:
        return {
            "success": True,
            "matched": False,
            "confidence": 0.0,
            "window_title": window_title,
            "catalog_total": _load_catalog().get("total"),
        }

    return {
        "success": True,
        "matched": True,
        "form_id": best["id"],
        "product": best.get("product"),
        "confidence": round(min(best_score, 1.0), 2),
        "toolbar_map": best.get("toolbar", {}),
        "f5_fields": best.get("f5_fields", []),
        "grids": best.get("grids", []),
        "trees": best.get("trees", []),
        "outlines": best.get("outlines", []),
        "notes": best.get("notes", ""),
        "selection_pattern": best.get("selection"),
        "curated": bool(best.get("curated")),
        "window_title": window_title,
    }

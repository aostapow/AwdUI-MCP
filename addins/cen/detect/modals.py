"""Detect active CEN modal type (lookup, search, message, detail)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional


@lru_cache(maxsize=1)
def _load_modals() -> list[dict[str, Any]]:
    path = Path(__file__).resolve().parents[1] / "knowledge" / "modals.json"
    return json.loads(path.read_text(encoding="utf-8")).get("modals", [])


def _element_blob(el: dict[str, Any]) -> str:
    return " ".join(
        str(el.get(k) or "")
        for k in ("automation_id", "name", "class_name", "role")
    ).lower()


def detect_modal(
    window_title: Optional[str] = None,
    elements: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    if elements is None:
        from tools.ui_automation import do_list_elements

        listed = do_list_elements(window_title=window_title or "", max_depth=8)
        if isinstance(listed, str):
            listed = json.loads(listed)
        elements = listed.get("elements") or []
        resolved = listed.get("resolved_window_title") or window_title or ""
    else:
        resolved = window_title or ""

    blobs = [_element_blob(el) for el in elements]
    control_blob = " ".join(blobs)
    class_blob = " ".join(
        str(el.get("class_name") or "").lower() for el in elements
    )
    title_blob = (window_title or "").lower()
    combined = f"{title_blob} {class_blob} {control_blob}".strip()

    best: Optional[dict[str, Any]] = None
    best_score = 0.0

    for modal in _load_modals():
        score = 0.0
        hint_hit = False
        for hint in modal.get("class_hints", []):
            h = hint.lower()
            if h in title_blob or h in class_blob:
                score += 0.45
                hint_hit = True
        controls = modal.get("controls") or []
        ctrl_hits = sum(1 for ctrl in controls if ctrl.lower() in control_blob)
        if controls:
            ratio = ctrl_hits / len(controls)
            score += ratio * 0.55
        if modal.get("grid") and modal["grid"].lower() in control_blob:
            score += 0.15
        if modal.get("confirm") and modal["confirm"].lower() in control_blob:
            score += 0.15
        # Parent forms may share one field name (txtconvenio) — need stronger signal
        if controls and ctrl_hits < 2 and not hint_hit:
            if not (modal.get("grid") and modal.get("confirm") and ctrl_hits >= 1):
                score *= 0.35
        if score > best_score:
            best_score = score
            best = modal

    if not best or best_score < 0.4:
        return {
            "success": True,
            "modal_open": False,
            "modal_type": None,
            "confidence": 0.0,
            "resolved_window_title": resolved,
        }

    return {
        "success": True,
        "modal_open": True,
        "modal_type": best["id"],
        "confidence": round(min(best_score, 1.0), 2),
        "recommended_flow": best.get("flow"),
        "confirm_control": best.get("confirm"),
        "cancel_control": best.get("cancel"),
        "grid_control": best.get("grid"),
        "notes": best.get("notes", ""),
        "resolved_window_title": resolved,
    }

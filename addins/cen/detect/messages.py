"""Classify COBIS dialog/message text against extracted catalog."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional


@lru_cache(maxsize=1)
def _load_messages() -> dict[str, Any]:
    base = Path(__file__).resolve().parents[1] / "knowledge"
    for name in ("messages_catalog.json", "messages.json"):
        path = base / name
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            if name == "messages.json":
                return {"by_category": data.get("actions", {}), "legacy": data}
            return data
    return {}


def classify_message(text: str = "") -> dict[str, Any]:
    """Classify visible dialog text into validation/confirm/success/security."""
    sample = (text or "").strip()
    if not sample:
        return {"success": False, "error": "text required"}

    low = sample.lower()
    catalog = _load_messages()
    by_cat = catalog.get("by_category") or {}

    best_cat = "unknown"
    best_score = 0.0
    for cat, messages in by_cat.items():
        if cat in ("ok", "cancel", "yes", "no"):
            continue
        for msg in messages:
            mlow = msg.lower()
            if mlow in low or low in mlow:
                score = min(len(mlow), len(low)) / max(len(mlow), len(low), 1)
                if score > best_score:
                    best_score = score
                    best_cat = cat

    legacy = catalog.get("legacy") or {}
    suggested_action = "ok"
    if best_cat in ("validation", "empty", "security"):
        suggested_action = "ok"
    elif best_cat == "confirm":
        suggested_action = "yes"
    elif best_cat == "success":
        suggested_action = "ok"

    for action, labels in (legacy.get("actions") or {}).items():
        if any(lbl.lower() in low for lbl in labels):
            suggested_action = action
            break

    return {
        "success": True,
        "text": sample,
        "category": best_cat,
        "confidence": round(min(best_score + 0.2, 1.0), 2) if best_score else 0.3,
        "suggested_action": suggested_action,
        "recommended_tool": f"cen_handle_dialog(action={suggested_action!r})",
    }


def match_dialog_from_ui(window_title: Optional[str] = None) -> dict[str, Any]:
    """Read focused/static text from dialog and classify."""
    from tools.ui_automation import do_list_elements, do_find_element

    listed = do_list_elements(window_title=window_title or "", max_depth=4)
    if isinstance(listed, str):
        listed = json.loads(listed)

    texts = []
    for el in listed.get("elements") or []:
        name = (el.get("name") or "").strip()
        if len(name) >= 8:
            texts.append(name)

    if not texts:
        return {"success": False, "error": "no dialog text found", "elements": 0}

    longest = max(texts, key=len)
    classified = classify_message(longest)
    return {
        **classified,
        "dialog_texts": texts[:5],
        "resolved_window_title": listed.get("resolved_window_title") or "",
    }

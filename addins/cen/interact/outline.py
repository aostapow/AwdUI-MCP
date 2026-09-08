"""COBISMSOutline hierarchy interaction."""
from __future__ import annotations

import re
from typing import Any, Optional


def parse_outline_text(text: str) -> dict[str, str]:
    """Parse 'code - name - NIVEL n' outline entries."""
    parts = [p.strip() for p in (text or "").split(" - ")]
    out: dict[str, str] = {"raw": text}
    if parts:
        out["code"] = parts[0]
    if len(parts) > 1:
        out["name"] = parts[1]
    for p in parts:
        m = re.search(r"NIVEL\s*(\d+)", p, re.I)
        if m:
            out["level"] = m.group(1)
    return out


def outline_select(
    automation_id: str = "otlOficiales",
    text_contains: str = "",
    window_title: Optional[str] = None,
) -> dict[str, Any]:
    from tools.ui_automation import do_click_element, do_list_elements

    listed = do_list_elements(window_title=window_title or "", max_depth=10)
    if isinstance(listed, str):
        import json
        listed = json.loads(listed)

    needle = (text_contains or "").lower()
    for el in listed.get("elements") or []:
        blob = f"{el.get('name')} {el.get('automation_id')}".lower()
        if "outline" in (el.get("class_name") or "").lower() or automation_id.lower() in blob:
            if not needle or needle in (el.get("name") or "").lower():
                click = do_click_element(
                    automation_id=el.get("automation_id") or automation_id,
                    name=el.get("name") or "",
                    window_title=window_title or "",
                )
                parsed = parse_outline_text(el.get("name") or "")
                return {"success": True, "click": click, "parsed": parsed, "element": el}

    return {"success": False, "error": "Outline node not found", "search": text_contains}


def outline_expand(
    automation_id: str = "otlOficiales",
    window_title: Optional[str] = None,
) -> dict[str, Any]:
    from tools.ui_automation import do_double_click_element

    return do_double_click_element(automation_id=automation_id, window_title=window_title or "")

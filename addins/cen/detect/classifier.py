"""Classify WinForms elements into COBIS CEN control types."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional


@lru_cache(maxsize=1)
def _load_controls() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "knowledge" / "controls.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _match_pattern(name: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if re.search(pat, name, re.IGNORECASE):
            return True
    return False


def classify_element(element: dict[str, Any]) -> dict[str, Any]:
    """Return CEN control classification for a UIA element dict."""
    catalog = _load_controls()
    class_name = (element.get("class_name") or "").strip()
    name = (element.get("name") or element.get("automation_id") or "").strip()
    role = (element.get("role") or "").strip()
    blob = f"{class_name} {name} {role}".lower()

    best: Optional[dict[str, Any]] = None
    best_score = 0.0

    for ctrl in catalog.get("controls", []):
        score = 0.0
        for cls in ctrl.get("classes", []):
            if cls.lower() in class_name.lower():
                score += 0.6
        if _match_pattern(name, ctrl.get("name_patterns", [])):
            score += 0.4
        if score > best_score:
            best_score = score
            best = ctrl

    if not best or best_score < 0.35:
        if name.lower().startswith("grd") or name.lower().startswith("gr_"):
            best = next(c for c in catalog["controls"] if c["id"] == "cobis_grid")
            best_score = 0.5
        elif role.lower() in ("combobox",):
            best = next((c for c in catalog["controls"] if c["id"] == "cobis_combo"), None)
            best_score = 0.4
        elif "tristatetreeview" in blob or name.lower().startswith("trv"):
            best = next((c for c in catalog["controls"] if c["id"] == "cobis_tristate_tree"), None)
            best_score = 0.45
        elif name.lower().startswith("picvisto"):
            best = next((c for c in catalog["controls"] if c["id"] == "cobis_grid_checkbox"), None)
            best_score = 0.5
        elif class_name.lower() == "usercontrol" or name.lower().startswith(("uc", "cmdmoneda")):
            best = next((c for c in catalog["controls"] if c["id"] == "cobis_user_control"), None)
            best_score = 0.4
        elif role.lower() == "checkbox" or name.lower().startswith("chk"):
            best = next((c for c in catalog["controls"] if c["id"] == "winforms_checkbox"), None)
            best_score = 0.4

    if not best:
        return {
            "cen_type": "unknown",
            "confidence": 0.0,
            "mcp_tools": ["discover_control_interaction", "spy_inspect"],
            "element": {"name": name, "class_name": class_name, "role": role},
        }

    return {
        "cen_type": best["id"],
        "confidence": round(min(best_score, 1.0), 2),
        "mcp_tools": best.get("mcp_tools", []),
        "f5_capable": bool(best.get("f5")),
        "index_base": best.get("index_base"),
        "notes": best.get("notes", ""),
        "element": {
            "name": name,
            "automation_id": element.get("automation_id", ""),
            "class_name": class_name,
            "role": role,
        },
    }


def classify_elements(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{**el, "cen": classify_element(el)} for el in elements]

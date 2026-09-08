"""Detect COBIS grid flavor from UIA metadata."""
from __future__ import annotations

import re
from typing import Any

GridType = str  # cobis_spread | cobis_grid | uia_table | unknown

_FARPOINT_HINTS = ("fpspread", "farpoint", "cobisspread", "sheet1")
_COBIS_GRID_HINTS = ("cobisgrid", "vsflex", "mshflex", "flexgrid")
_SPREAD_NAME_RE = re.compile(r"row\s*\d+.*column\s*\d+", re.IGNORECASE)


def _blob(element: dict[str, Any]) -> str:
    parts = [
        element.get("class_name") or "",
        element.get("name") or "",
        element.get("automation_id") or "",
        element.get("accessible_description") or "",
        element.get("role") or "",
    ]
    return " ".join(parts).lower()


def detect_grid_type(element: dict[str, Any], sample_child_names: list[str] | None = None) -> dict[str, Any]:
    """Classify grid control for reader selection."""
    blob = _blob(element)
    role = (element.get("role") or "").lower()
    child_blob = " ".join(sample_child_names or []).lower()

    if any(h in blob for h in _FARPOINT_HINTS) or _SPREAD_NAME_RE.search(child_blob):
        return {
            "grid_type": "cobis_spread",
            "confidence": 0.9,
            "index_base": 1,
            "reader": "farpoint_uia",
        }
    if any(h in blob for h in _COBIS_GRID_HINTS):
        return {
            "grid_type": "cobis_grid",
            "confidence": 0.85,
            "index_base": 1,
            "reader": "spatial_uia",
        }
    if role in ("table", "datagrid", "grid"):
        return {
            "grid_type": "uia_table",
            "confidence": 0.7,
            "index_base": 0,
            "reader": "core_read_table",
        }
    if (element.get("automation_id") or element.get("name") or "").lower().startswith("grd"):
        return {
            "grid_type": "cobis_grid",
            "confidence": 0.6,
            "index_base": 1,
            "reader": "spatial_uia",
        }
    return {
        "grid_type": "unknown",
        "confidence": 0.3,
        "index_base": 1,
        "reader": "spatial_uia",
    }

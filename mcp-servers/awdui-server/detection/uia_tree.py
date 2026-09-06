"""Shared UIA descendant walk helpers."""
from __future__ import annotations

from typing import Any, Iterator, Optional


def _walk_control_tree(root, max_nodes: int = 8000) -> Iterator:
    """Yield pywinauto wrapper descendants under *root*."""
    count = 0
    try:
        for desc in root.descendants():
            if count >= max_nodes:
                break
            count += 1
            yield desc
    except Exception:
        return


def _wrap_raw(raw) -> Optional[object]:
    from detection.backends.uia_backend import _pywinauto_to_element

    try:
        return _pywinauto_to_element(raw)
    except Exception:
        return None


def element_fields(raw_or_det) -> Optional[dict[str, Any]]:
    """Normalize DetectedElement or pywinauto wrapper to a flat field dict."""
    if raw_or_det is None:
        return None
    if hasattr(raw_or_det, "to_dict"):
        d = raw_or_det.to_dict()
        return {
            "name": d.get("name", ""),
            "role": d.get("role", ""),
            "x": int(d.get("x", 0) or 0),
            "y": int(d.get("y", 0) or 0),
            "width": int(d.get("width", 0) or 0),
            "height": int(d.get("height", 0) or 0),
            "automation_id": d.get("automation_id", "") or "",
            "value": d.get("value", "") or "",
        }
    if hasattr(raw_or_det, "element_info"):
        info = raw_or_det.element_info
        rect = info.rectangle
        return {
            "name": info.name or "",
            "role": info.control_type or "",
            "x": int(rect.left),
            "y": int(rect.top),
            "width": int(rect.right - rect.left),
            "height": int(rect.bottom - rect.top),
            "automation_id": getattr(info, "automation_id", "") or "",
            "value": "",
        }
    return None

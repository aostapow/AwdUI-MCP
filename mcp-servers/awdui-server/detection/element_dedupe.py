"""Deduplicate UIA elements (UWP overlay / dual-tree duplicates)."""
from __future__ import annotations

from detection.element_model import DetectedElement


def _rank_element(d: DetectedElement) -> tuple:
    area = max(0, int(d.width)) * max(0, int(d.height))
    enabled = 1 if d.enabled else 0
    visible = 1 if d.visible else 0
    xaml = 1 if (d.framework_id or "").upper() == "XAML" else 0
    aid = (d.automation_id or "").strip()
    # Full-screen LightDismiss overlay duplicates the tree — prefer real controls.
    not_light_dismiss = 0 if aid == "LightDismiss" else 1
    return (xaml, not_light_dismiss, enabled, visible, area)


def dedupe_detected_elements(elements: list[DetectedElement]) -> list[DetectedElement]:
    """Keep one element per automation_id when UWP exposes duplicate overlay trees."""
    best_by_aid: dict[str, DetectedElement] = {}
    without_aid: list[DetectedElement] = []
    for d in elements:
        aid = (d.automation_id or "").strip()
        if not aid:
            without_aid.append(d)
            continue
        cur = best_by_aid.get(aid)
        if cur is None or _rank_element(d) > _rank_element(cur):
            best_by_aid[aid] = d
    return list(best_by_aid.values()) + without_aid

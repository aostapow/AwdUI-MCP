"""Tests for ancestor_automation_id subtree filter."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"))

from detection.element_model import DetectedElement
from detection.element_scope import filter_elements_by_ancestor


def _elem(aid: str, x: int, y: int, w: int = 50, h: int = 20) -> DetectedElement:
    return DetectedElement(
        name=aid,
        role="Button",
        automation_id=aid,
        x=x,
        y=y,
        width=w,
        height=h,
    )


def test_filter_elements_by_ancestor_keeps_inside():
    parent = _elem("pane", 100, 100, 200, 200)
    inside = _elem("btn", 120, 120)
    outside = _elem("other", 400, 400)
    kept, meta = filter_elements_by_ancestor([parent, inside, outside], "pane")
    aids = {e.automation_id for e in kept}
    assert "btn" in aids
    assert "other" not in aids
    assert meta["ancestor_found"] is True
    assert meta["filtered_out"] == 1

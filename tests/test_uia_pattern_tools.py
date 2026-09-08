"""Tests for UIA pattern MCP wrappers (Block A)."""
from __future__ import annotations

import pytest


def test_do_scroll_into_view(monkeypatch):
    from tools.uia_pattern_tools import do_scroll_into_view

    monkeypatch.setattr(
        "tools.uia_pattern_tools._resolve_control",
        lambda aid, wt: (object(), None, {}, {"resolved_title": "AST"}),
    )
    monkeypatch.setattr(
        "detection.uia_patterns.scroll_item_into_view",
        lambda _r: {
            "success": True,
            "method": "ScrollItem.ScrollIntoView",
            "name": "Row 1",
            "x": 10,
            "y": 20,
        },
    )

    out = do_scroll_into_view("item1", window_title="AST")
    assert out["success"] is True
    assert out["method"] == "ScrollItem.ScrollIntoView"
    assert out["resolved_window_title"] == "AST"


def test_do_realize_virtualized_item(monkeypatch):
    from tools.uia_pattern_tools import do_realize_virtualized_item

    monkeypatch.setattr(
        "tools.uia_pattern_tools._resolve_control",
        lambda aid, wt: (object(), None, {}, {"resolved_title": "Calc"}),
    )
    monkeypatch.setattr(
        "detection.uia_patterns.realize_virtualized_item",
        lambda _r: {
            "success": True,
            "method": "VirtualizedItem.Realize",
            "name": "Item 99",
            "role": "ListItem",
        },
    )

    out = do_realize_virtualized_item("virtItem")
    assert out["success"] is True
    assert out["role"] == "ListItem"


def test_do_find_item_by_property(monkeypatch):
    from tools.uia_pattern_tools import do_find_item_by_property

    calls = []

    def fake_resolve(aid, wt):
        calls.append(aid)
        return object(), None, {}, {"resolved_title": "AST"}

    monkeypatch.setattr("tools.uia_pattern_tools._resolve_control", fake_resolve)
    monkeypatch.setattr(
        "detection.uia_patterns.find_item_by_property",
        lambda container, property_name, value, start_after_raw=None: {
            "success": True,
            "method": "ItemContainer.FindItemByProperty",
            "property": property_name,
            "value": value,
            "name": value,
            "automation_id": "row2",
            "start_after_seen": start_after_raw is not None,
        },
    )

    out = do_find_item_by_property(
        "gcGrillaActividades",
        property_name="name",
        property_value="BM-MANT",
        start_after_automation_id="row1",
    )
    assert out["success"] is True
    assert out["method"] == "ItemContainer.FindItemByProperty"
    assert calls == ["gcGrillaActividades", "row1"]


def test_do_scroll_element_percent(monkeypatch):
    from tools.uia_pattern_tools import do_scroll_element

    monkeypatch.setattr(
        "tools.uia_pattern_tools._resolve_control",
        lambda aid, wt: (object(), None, {}, {}),
    )
    captured = {}

    def fake_scroll(raw, **kwargs):
        captured.update(kwargs)
        return {
            "success": True,
            "method": "Scroll.SetScrollPercent",
            "horizontal_percent": kwargs.get("horizontal_percent"),
            "vertical_percent": kwargs.get("vertical_percent"),
        }

    monkeypatch.setattr("detection.uia_patterns.apply_scroll_pattern", fake_scroll)

    out = do_scroll_element("listPane", horizontal_percent=10, vertical_percent=80)
    assert out["success"] is True
    assert captured["horizontal_percent"] == 10
    assert captured["vertical_percent"] == 80


def test_do_scroll_into_view_missing_id():
    from tools.uia_pattern_tools import do_scroll_into_view

    out = do_scroll_into_view("")
    assert out["success"] is False
    assert "not found" in out["error"].lower()


def test_do_scroll_element_clicks_alias(monkeypatch):
    from tools.uia_pattern_tools import do_scroll_element

    monkeypatch.setattr(
        "tools.uia_pattern_tools._resolve_raw_control",
        lambda **kwargs: (object(), {}, "listPane", {}),
    )
    captured = {}

    def fake_scroll(raw, **kwargs):
        captured.update(kwargs)
        return {"success": True, "method": "Scroll.Scroll"}

    monkeypatch.setattr("detection.uia_patterns.apply_scroll_pattern", fake_scroll)

    out = do_scroll_element("listPane", clicks=4)
    assert out["success"] is True
    assert captured["repeat"] == 4


def test_do_scroll_element_fallback_on_pattern_failure(monkeypatch):
    from tools.uia_pattern_tools import do_scroll_element

    monkeypatch.setattr(
        "tools.uia_pattern_tools._resolve_raw_control",
        lambda **kwargs: (object(), {}, "docPane", {}),
    )
    monkeypatch.setattr(
        "detection.uia_patterns.apply_scroll_pattern",
        lambda *_a, **_k: {"success": False, "error": "COM ScrollPattern failed"},
    )
    monkeypatch.setattr(
        "detection.uia_patterns._element_dict",
        lambda _r: {"x": 100, "y": 50, "width": 200, "height": 400},
    )
    monkeypatch.setattr(
        "tools.input_tools.do_scroll",
        lambda x, y, direction, pages=None, amount=None: {
            "action": "scroll",
            "verified": True,
        },
    )

    out = do_scroll_element("docPane", direction="down", amount="large")
    assert out["success"] is True
    assert out["method"] == "scroll_fallback_coords"
    assert out["fallback_reason"] == "COM ScrollPattern failed"


def test_do_scroll_element_uses_scrollable_ancestor(monkeypatch):
    from tools.uia_pattern_tools import do_scroll_element

    leaf = object()
    ancestor = object()
    monkeypatch.setattr(
        "tools.uia_pattern_tools._resolve_raw_control",
        lambda **kwargs: (leaf, {}, "message-pane", {}),
    )
    monkeypatch.setattr(
        "detection.uia_patterns._has_pattern",
        lambda raw, name: raw is ancestor and name == "Scroll",
    )
    monkeypatch.setattr(
        "detection.uia_patterns.find_scrollable_ancestor",
        lambda raw: ancestor if raw is leaf else None,
    )
    captured = {}

    def fake_scroll(raw, **kwargs):
        captured["raw"] = raw
        return {"success": True, "method": "Scroll.Scroll", "direction": "up"}

    monkeypatch.setattr("detection.uia_patterns.apply_scroll_pattern", fake_scroll)

    out = do_scroll_element("message-pane", direction="up", amount="large")
    assert out["success"] is True
    assert captured["raw"] is ancestor
    assert out.get("scroll_via") == "ancestor"

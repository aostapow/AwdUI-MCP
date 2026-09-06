"""Tests for Microsoft UIA control map (static JSON + discover merge)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"))

from detection.control_interaction import discover_from_element
from detection.uia_control_map import (
    get_control_spec,
    list_control_types,
    load_control_map,
    merge_official_strategies,
    official_strategies,
)


class TestUiaControlMapJson:
    def test_json_loads_and_has_controls(self):
        data = load_control_map()
        assert data["schema_version"] >= 1
        assert "learn.microsoft.com" in data["source_url"]
        types = list_control_types()
        assert len(types) >= 38
        assert "Button" in types
        assert "AppBar" in types
        assert "SemanticZoom" in types

    def test_button_ms_patterns(self):
        spec = get_control_spec("Button")
        assert spec is not None
        cond = spec["patterns_ms"]["conditional"]
        assert "Invoke" in cond
        assert "Toggle" in cond

    def test_unknown_role_returns_none(self):
        assert get_control_spec("NotARealControl") is None

    def test_json_valid_on_disk(self):
        from detection.uia_control_map import validate_control_map

        errors = validate_control_map()
        assert errors == []

    def test_all_ms_types_present(self):
        from detection.uia_control_map import OFFICIAL_MS_CONTROL_TYPES, list_control_types

        present = set(list_control_types())
        missing = OFFICIAL_MS_CONTROL_TYPES - present
        assert not missing, f"missing MS types: {sorted(missing)}"


class TestOfficialStrategies:
    def test_button_invoke_when_pattern_present(self):
        strats = official_strategies("Button", {"Invoke"})
        ids = [s["id"] for s in strats]
        assert "map_invoke" in ids
        assert any(s.get("phase") == "fallback" for s in strats)

    def test_button_without_live_patterns_still_has_medium_entries(self):
        strats = official_strategies("Button", set())
        assert any(s["id"] == "map_invoke" for s in strats)

    def test_appbar_in_map(self):
        strats = official_strategies("AppBar", {"Toggle", "ExpandCollapse"})
        ids = [s["id"] for s in strats]
        assert "map_appbar_toggle" in ids

    def test_merge_adds_without_duplicating_ids(self):
        base = [{"id": "button_invoke", "tools": ["invoke_element"], "steps": [], "phase": "act", "confidence": "high"}]
        meta = merge_official_strategies(base, "Button", {"Invoke"})
        assert meta["in_map"] is True
        assert meta["strategies_added"] >= 1
        ids = [s["id"] for s in base]
        assert "map_invoke" in ids
        assert ids.count("map_invoke") == 1


class TestDiscoverMergesOfficialMap:
    def test_discover_includes_official_map_metadata(self):
        report = discover_from_element(
            {"automation_id": "btnOk", "role": "Button", "patterns": ["Invoke"]},
        )
        omap = report.get("official_map") or {}
        assert omap.get("in_map") is True
        assert omap.get("strategies_added", 0) >= 1
        ids = [s["id"] for s in report["strategies"]]
        assert "button_invoke" in ids or "map_invoke" in ids

    def test_discover_text_shows_ms_map_line(self):
        from detection.control_interaction import format_discovery_report

        report = discover_from_element({"role": "ComboBox", "patterns": ["ExpandCollapse"]})
        text = format_discovery_report(report)
        assert "MS map" in text or "uia_control_map" in text

    def test_semantic_zoom_covered(self):
        report = discover_from_element(
            {"role": "SemanticZoom", "patterns": ["Toggle"]},
        )
        assert report["official_map"]["in_map"] is True
        ids = [s["id"] for s in report["strategies"]]
        assert any("semzoom" in i or "map_" in i for i in ids)

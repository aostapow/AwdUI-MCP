"""Tests for spy_bridge property normalization."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"))


class TestSpyBridge:
    def test_spy_props_to_element(self):
        from tools.spy_bridge import spy_props_to_element
        elem = spy_props_to_element({
            "name": "Seis",
            "role": "Button",
            "automation_id": "num6Button",
            "x": 100,
            "y": 200,
            "width": 96,
            "height": 63,
            "is_enabled": True,
            "is_offscreen": False,
            "patterns": {"Invoke": {"supported": True}},
        })
        assert elem["name"] == "Seis"
        assert elem["automation_id"] == "num6Button"
        assert elem["clickable_x"] == 148
        assert elem["backend"] == "spy"

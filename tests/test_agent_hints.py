"""Tests for agent_hints parsing."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"))

from detection.agent_hints import hint_preferred_tool, hint_verify_automation_id, parse_agent_hints


class TestAgentHints:
    def test_parse_key_value_lines(self):
        parsed = parse_agent_hints(
            "verify_automation_id: CalculatorResults\n"
            "note: display after keypad\n"
        )
        assert parsed["verify_automation_id"] == "CalculatorResults"
        assert parsed["note"] == "display after keypad"

    def test_parse_json(self):
        parsed = parse_agent_hints('{"verify_automation_id": "Foo"}')
        assert parsed["verify_automation_id"] == "Foo"

    def test_hint_verify_automation_id(self):
        assert hint_verify_automation_id("verify_target: Bar\n") == "Bar"

    def test_hint_preferred_tool_aliases(self):
        assert hint_preferred_tool("preferred_tool: select_control_item") == "select_control_item"

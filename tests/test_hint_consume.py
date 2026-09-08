"""Tests for automatic agent_hints consumption."""
from __future__ import annotations

import os
import sys
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"))

from detection.agent_hints import hint_click_mode, hint_preferred_tool, parse_agent_hints
from detection.control_interaction import discover_from_element
from detection.hint_consume import (
    apply_hint_click_mode,
    apply_hints_to_discovery_report,
    attach_hints_to_result,
)


class TestHintPreferredTool:
    def test_metodo_preferido(self):
        assert hint_preferred_tool("metodo_preferido: click_element") == "click_element"

    def test_pipe_suffix_ignored(self):
        assert hint_preferred_tool("metodo_preferido: invoke_element | click_element") == "invoke_element"

    def test_click_mode_from_preferred(self):
        assert hint_click_mode("metodo_preferido: click_element") == "click"
        assert hint_click_mode("metodo_preferido: invoke_element") == "invoke"

    def test_avoid_invoke_flag(self):
        assert hint_click_mode("avoid_invoke: yes") == "click"


class TestApplyHintsToDiscovery:
    def test_promotes_strategy_with_preferred_tool(self):
        report = discover_from_element(
            {
                "automation_id": "btnOk",
                "role": "Button",
                "patterns": ["Invoke"],
            },
            repo_hints="metodo_preferido: click_element\n",
        )
        assert report.get("hint_preferred_tool") == "click_element"
        assert report.get("hint_applied") == "recommended_strategy"
        assert "click_element" in (report.get("recommended") or {}).get("tools", [])

    def test_no_promotion_without_match(self):
        base = discover_from_element(
            {"automation_id": "x", "role": "Button", "patterns": ["Invoke"]},
            repo_hints="",
        )
        out = apply_hints_to_discovery_report(
            base,
            "metodo_preferido: nonexistent_tool_xyz\n",
        )
        assert out.get("hint_applied") is None


class TestAttachHintsToResult:
    def test_attaches_from_repo_path(self):
        with mock.patch(
            "detection.repo_store.get_agent_hints",
            return_value="verify_automation_id: Display1\nmetodo_preferido: invoke_element\n",
        ):
            out = attach_hints_to_result(
                {"found": True, "repo_path": "main/btn", "elements": [{"automation_id": "btn"}]},
            )
        assert "verify_automation_id" in out["agent_hints"]
        assert out["hint_preferred_tool"] == "invoke_element"
        assert out["hint_verify_automation_id"] == "Display1"


class TestApplyHintClickMode:
    def test_invoke_only_on_failure(self):
        elem = {"automation_id": "btn", "name": "OK"}
        out = apply_hint_click_mode(
            elem=elem,
            click_mode="invoke",
            invoke_fn=lambda: {"success": False},
            click_fn=lambda: {"success": True, "method": "click"},
        )
        assert out["success"] is False
        assert out.get("hint_applied") == "invoke_mode=invoke"

    def test_click_mode_skips_invoke(self):
        elem = {"automation_id": "btn"}
        invoked = {"flag": False}

        def invoke_fn():
            invoked["flag"] = True
            return {"success": True, "method": "InvokePattern"}

        out = apply_hint_click_mode(
            elem=elem,
            click_mode="click",
            invoke_fn=invoke_fn,
            click_fn=lambda: {"success": True, "method": "click"},
        )
        assert out["success"] is True
        assert invoked["flag"] is False
        assert out.get("hint_applied") == "click_mode=click"

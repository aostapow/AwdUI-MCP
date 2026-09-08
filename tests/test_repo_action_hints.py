"""Tests for repo_action applying agent_hints on Click."""
from __future__ import annotations

import os
import sys
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"))


def _resolved_elem():
    return {
        "found": True,
        "element": {
            "name": "OK",
            "role": "Button",
            "automation_id": "btnOk",
            "x": 10,
            "y": 20,
            "width": 40,
            "height": 20,
        },
        "swf_class": "SwfButton",
        "method": "uia",
    }


class TestRepoActionHintClick:
    def test_click_mode_skips_invoke(self):
        with mock.patch("tools.repo_action.do_repo_resolve", return_value=_resolved_elem()), mock.patch(
            "detection.hint_consume.resolve_object_hints",
            return_value={
                "agent_hints": "metodo_preferido: click_element",
                "hint_click_mode": "click",
            },
        ), mock.patch(
            "detection.hint_consume.attach_hints_to_result",
            side_effect=lambda r, **kw: r,
        ), mock.patch(
            "tools.repo_action._click_coords",
            return_value=(30, 30),
        ), mock.patch("tools.input_tools.do_click") as click_mock, mock.patch(
            "tools.ui_automation.do_invoke_on_element",
        ) as invoke_mock:
            from tools.repo_action import do_repo_action

            out = do_repo_action("main/btnOk", "Click")
        assert out["success"] is True
        assert out["action"] == "click"
        assert out.get("hint_applied") == "click_mode=click"
        click_mock.assert_called_once()
        invoke_mock.assert_not_called()

    def test_invoke_only_no_coord_fallback(self):
        with mock.patch("tools.repo_action.do_repo_resolve", return_value=_resolved_elem()), mock.patch(
            "detection.hint_consume.resolve_object_hints",
            return_value={
                "agent_hints": "metodo_preferido: invoke_element",
                "hint_click_mode": "invoke",
            },
        ), mock.patch(
            "detection.hint_consume.attach_hints_to_result",
            side_effect=lambda r, **kw: r,
        ), mock.patch(
            "tools.ui_automation.do_invoke_on_element",
            return_value={"success": False},
        ), mock.patch("tools.input_tools.do_click") as click_mock:
            from tools.repo_action import do_repo_action

            out = do_repo_action("main/btnOk", "Click")
        assert out["success"] is False
        assert "invoke only" in out.get("error", "").lower()
        click_mock.assert_not_called()

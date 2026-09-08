"""Tests for act_on_control orchestration."""
import os
import sys
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"))

from tools.act_tools import do_act_on_control


def test_act_on_control_invoke():
    with mock.patch("tools.ui_automation.do_invoke_element", return_value={"success": True, "method": "InvokePattern", "elapsed_ms": 120}):
        with mock.patch("detection.hint_consume.resolve_object_hints", return_value={"hint_parsed": {}, "hint_click_mode": "auto"}):
            with mock.patch("detection.hint_consume.attach_hints_to_result", side_effect=lambda r, **k: r):
                out = do_act_on_control(action="invoke", automation_id="btnOk")
    assert out["success"] is True
    assert out["acted_via"] == "InvokePattern"

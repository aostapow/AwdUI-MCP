"""Tests for wait_tools."""
import os
import sys
from unittest import mock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"))


class TestWaitForElement:
    @mock.patch("tools.ui_automation.do_find_element")
    def test_found_on_second_poll(self, mock_find):
        mock_find.side_effect = [
            {"found": False, "elements": []},
            {"found": True, "elements": [{"name": "OK", "role": "Button"}]},
        ]
        from tools.wait_tools import do_wait_for_element

        out = do_wait_for_element(automation_id="btnOk", timeout_ms=2000, poll_ms=50)
        assert out["success"] is True
        assert mock_find.call_count >= 2

    @mock.patch("tools.ui_automation.do_find_element")
    def test_timeout(self, mock_find):
        mock_find.return_value = {"found": False, "elements": []}
        from tools.wait_tools import do_wait_for_element

        out = do_wait_for_element(automation_id="missing", timeout_ms=100, poll_ms=20)
        assert out["success"] is False
        assert out["code"] == "timeout"


class TestWaitForCondition:
    @mock.patch("tools.wait_tools._read_properties")
    def test_matches_on_second_poll(self, mock_read):
        mock_read.side_effect = [
            {"name": "Se muestra 0"},
            {"name": "Se muestra 7", "automation_id": "CalculatorResults"},
        ]
        from tools.wait_tools import do_wait_for_condition

        out = do_wait_for_condition(
            property="name",
            expected_value="Se muestra 7",
            automation_id="CalculatorResults",
            timeout_ms=2000,
            poll_ms=50,
        )
        assert out["success"] is True
        assert out["actual"] == "Se muestra 7"

    @mock.patch("tools.wait_tools._read_properties")
    def test_bool_enabled(self, mock_read):
        mock_read.return_value = {"is_enabled": True}
        from tools.wait_tools import do_wait_for_condition

        out = do_wait_for_condition(
            property="isEnabled",
            expected_value="true",
            automation_id="clearButton",
            timeout_ms=500,
            poll_ms=20,
        )
        assert out["success"] is True


class TestElementExists:
    @mock.patch("tools.ui_automation.do_find_element")
    def test_returns_bool(self, mock_find):
        mock_find.return_value = {"found": True, "elements": [{}]}
        from tools.wait_tools import do_element_exists

        assert do_element_exists(automation_id="x") is True


class TestPropertyHelpers:
    def test_extract_toggle_checked(self):
        from tools.wait_tools import _extract_property

        props = {"patterns": {"Toggle": {"state": "On"}}}
        assert _extract_property(props, "isChecked") == "true"


class TestWithTimeoutWrapper:
    @mock.patch("tools.wait_tools.do_wait_for_element")
    def test_wait_for_element_uses_timeout_kwarg(self, mock_wait):
        mock_wait.return_value = {
            "success": True,
            "elapsed_ms": 10,
            "attempts": 1,
            "element": {"name": "OK"},
        }
        from tools.safety import with_timeout

        result = with_timeout(
            lambda: mock_wait(automation_id="btnOk", timeout_ms=100, poll_ms=20),
            timeout=2.0,
        )
        assert result["success"] is True


class TestPropertyMatches:
    def test_property_matches_contains(self):
        from tools.wait_tools import _property_matches

        assert _property_matches("Se muestra 7", "muestra 7", "name") is True

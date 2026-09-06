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


class TestWithTimeoutWrapper:
    @staticmethod
    def _register_tools():
        from tools.wait_tools import register

        tools: dict = {}

        class _Srv:
            def tool(self):
                def deco(fn):
                    tools[fn.__name__] = fn
                    return fn

                return deco

        register(_Srv())
        return tools

    @mock.patch("tools.safety.with_timeout")
    @mock.patch("tools.wait_tools.do_wait_for_input_idle")
    def test_wait_for_input_idle_passes_timeout_kwarg(self, mock_idle, mock_wt):
        mock_idle.return_value = {
            "success": True,
            "elapsed_ms": 5,
            "pid": 1,
            "window_title": "Calculadora",
        }
        mock_wt.side_effect = lambda fn, timeout=10.0, default=object(): fn()

        tools = self._register_tools()
        out = tools["wait_for_input_idle"](window_title="Calculadora", timeout_ms=2500)
        assert "OK idle" in out
        assert mock_wt.call_count == 1
        _args, kwargs = mock_wt.call_args
        assert kwargs.get("timeout") == max(2500 / 1000.0, 1.0) + 5.0
        assert "timeout_s" not in kwargs

    @mock.patch("tools.safety.with_timeout")
    @mock.patch("tools.wait_tools.do_wait_for_element")
    def test_wait_for_element_passes_timeout_kwarg(self, mock_wait, mock_wt):
        mock_wait.return_value = {
            "success": True,
            "elapsed_ms": 10,
            "attempts": 1,
            "element": {"name": "OK"},
        }
        mock_wt.side_effect = lambda fn, timeout=10.0, default=object(): fn()

        tools = self._register_tools()
        out = tools["wait_for_element"](automation_id="btnOk", timeout_ms=500)
        assert "OK found" in out
        _args, kwargs = mock_wt.call_args
        assert kwargs.get("timeout") == max(500 / 1000.0, 1.0) + 5.0
        assert "timeout_s" not in kwargs


class TestPropertyHelpers:
    def test_extract_toggle_checked(self):
        from tools.wait_tools import _extract_property

        props = {"patterns": {"Toggle": {"state": "On"}}}
        assert _extract_property(props, "isChecked") == "true"


class TestPropertyMatches:
    def test_property_matches_contains(self):
        from tools.wait_tools import _property_matches

        assert _property_matches("Se muestra 7", "muestra 7", "name") is True

"""Tests for element_activate fallback chain."""
import os
import sys
from unittest import mock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"))


class TestActivateElement:
    @mock.patch("detection.uia_patterns.apply_pattern_action")
    def test_invoke_success(self, mock_apply):
        mock_apply.return_value = {"success": True, "method": "InvokePattern.Invoke"}
        from detection.element_activate import activate_element

        out = activate_element(object(), mode="auto")
        assert out["success"] is True
        assert "Invoke" in out["method"] or out.get("pattern") == "Invoke"

    @mock.patch("tools.input_tools.do_click")
    @mock.patch("detection.backends.uia_backend._get_clickable_point", return_value=(10, 20))
    @mock.patch("detection.uia_patterns.apply_pattern_action")
    def test_falls_back_to_uia_click(self, mock_apply, _pt, mock_click):
        mock_apply.return_value = {"success": False, "error": "no pattern"}
        from detection.element_activate import activate_element

        raw = mock.MagicMock()
        raw.element_info.element = object()
        out = activate_element(raw, mode="auto")
        assert out["success"] is True
        assert out["method"] == "uia_click"
        mock_click.assert_called_once_with(10, 20)

    @mock.patch("detection.uia_patterns.apply_pattern_action")
    def test_strict_patterns_blocks_without_coords(self, mock_apply):
        mock_apply.return_value = {"success": False, "error": "no"}
        from detection.element_activate import activate_element

        raw = mock.MagicMock()
        raw.element_info.element = object()
        with mock.patch("detection.backends.uia_backend._get_clickable_point", return_value=(None, None)):
            with mock.patch("detection.backends.uia_backend._pywinauto_to_element", return_value=None):
                out = activate_element(
                    raw,
                    mode="auto",
                    strict_patterns=True,
                    automation_id="btnOk",
                )
        assert out["success"] is False

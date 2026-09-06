"""Unit tests for form and session tools."""
import json
import sys
from unittest import mock

sys.path.insert(0, "mcp-servers/awdui-server")


class TestFormTools:
    @mock.patch("tools.ui_automation.do_set_element_value")
    def test_fill_form_success(self, mock_set):
        from tools.form_tools import do_fill_form

        mock_set.return_value = {"success": True}
        result = do_fill_form([
            {"automation_id": "txtA", "value": "hello"},
            {"name": "FieldB", "value": "42"},
        ])
        assert result["success"]
        assert result["filled"] == 2
        assert mock_set.call_count == 2

    def test_fill_form_empty(self):
        from tools.form_tools import do_fill_form

        result = do_fill_form([])
        assert not result["success"]


class TestSessionTools:
    @mock.patch("tools.target_window.get_target", return_value="")
    def test_check_no_target(self, _gt):
        from tools.session_tools import do_check_session_status

        result = do_check_session_status()
        assert result["success"]
        assert not result["target_set"]

    @mock.patch("tools.target_window.set_target")
    @mock.patch("detection.uia_tree_cache.invalidate_all")
    @mock.patch("tools.highlight.clear_highlight")
    @mock.patch("detection.orchestrator.clear_tree_cache")
    def test_release_all(self, *_mocks):
        from tools.session_tools import do_release_all

        result = do_release_all()
        assert result["success"]

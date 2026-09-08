"""Tests for ensure_client_focus (Win32 Document/Edit keyboard target)."""
from __future__ import annotations

import os
import sys
from unittest import mock

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"),
)


class TestEnsureClientFocus:
    def setup_method(self):
        from tools import target_window

        target_window._target_window = "Bloc de notas"
        target_window._focus_policy = "minimal"

    def teardown_method(self):
        from tools import target_window

        target_window._target_window = None

    def test_already_focused_on_document(self):
        doc = {"role": "Document", "name": "Editor", "automation_id": "15"}
        with mock.patch(
            "tools.ui_automation.do_get_focused_element",
            return_value={"found": True, "element": doc},
        ):
            from tools.client_focus import ensure_client_focus

            out = ensure_client_focus()
        assert out["success"] is True
        assert out["method"] == "already_focused"

    def test_set_focus_when_needed(self):
        doc = {"role": "Document", "name": "Editor", "automation_id": "15", "width": 800, "height": 600}
        with mock.patch(
            "tools.ui_automation.do_get_focused_element",
            side_effect=[
                {"found": True, "element": {"role": "MenuBar", "name": "Aplicación"}},
                {"found": True, "element": doc},
            ],
        ), mock.patch(
            "tools.ui_automation.do_find_element",
            return_value={"found": True, "elements": [doc]},
        ), mock.patch(
            "detection.backends.uia_backend.get_uia_backend",
        ) as backend_factory:
            backend = mock.MagicMock()
            backend.focus_element.return_value = {"success": True, "method": "SetFocus"}
            backend_factory.return_value = backend
            from tools.client_focus import ensure_client_focus

            out = ensure_client_focus()
        assert out["success"] is True
        assert out["method"] == "SetFocus"
        backend.focus_element.assert_called_once()

    def test_bbox_fallback_when_set_focus_fails(self):
        doc = {
            "role": "Document",
            "name": "Editor",
            "automation_id": "15",
            "width": 800,
            "height": 600,
            "x": 100,
            "y": 100,
        }
        with mock.patch(
            "tools.ui_automation.do_get_focused_element",
            side_effect=[
                {"found": True, "element": {"role": "MenuBar"}},
                {"found": True, "element": doc},
            ],
        ), mock.patch(
            "tools.ui_automation.do_find_element",
            return_value={"found": True, "elements": [doc]},
        ), mock.patch(
            "detection.backends.uia_backend.get_uia_backend",
        ) as backend_factory, mock.patch(
            "tools.ui_automation._click_coords",
            return_value=(400, 300),
        ), mock.patch(
            "tools.input_tools.do_click",
            return_value={"success": True},
        ):
            backend = mock.MagicMock()
            backend.focus_element.return_value = {"success": False, "error": "fail"}
            backend_factory.return_value = backend
            from tools.client_focus import ensure_client_focus

            out = ensure_client_focus()
        assert out["success"] is True
        assert out["method"] == "ClientInput_bbox_fallback"

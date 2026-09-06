"""Tests for Block C session/cache tools."""
from __future__ import annotations

import json
from unittest import mock


def test_element_exists_tool_message():
    from tools.wait_tools import do_element_exists

    with mock.patch("tools.ui_automation.do_find_element") as mock_find:
        mock_find.return_value = {"found": True, "elements": [{}]}
        assert do_element_exists(automation_id="btnOk") is True
        mock_find.return_value = {"found": False, "elements": []}
        assert do_element_exists(automation_id="missing") is False


def test_invalidate_cache_all():
    from tools.wait_tools import do_invalidate_uia_cache

    out = do_invalidate_uia_cache()
    assert out["success"] is True
    assert out["invalidated"] == "all"
    assert "details" in out


def test_check_session_status_no_target():
    from tools.session_tools import do_check_session_status

    with mock.patch("tools.target_window.get_target", return_value=""):
        out = do_check_session_status()
    assert out["success"] is True
    assert out["target_set"] is False


def test_check_session_status_alive(monkeypatch):
    from tools.session_tools import do_check_session_status

    monkeypatch.setattr("tools.target_window.get_target", lambda: "Calculadora")
    monkeypatch.setattr("tools.windows.resolve_window_handle", lambda _t: 12345)
    monkeypatch.setattr("tools.spy_bridge.spy_available", lambda: True)

    out = do_check_session_status()
    assert out["target_alive"] is True
    assert out["target_hwnd"] == 12345
    assert out["spy_available"] is True

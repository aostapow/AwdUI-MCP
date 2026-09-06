"""Tests for WinApp app_id session registry."""
from __future__ import annotations

from unittest import mock

import pytest


@pytest.fixture(autouse=True)
def _clear_apps():
    from tools.app_session import clear_apps

    clear_apps()
    yield
    clear_apps()


class TestAppSession:
    def test_normalize_index(self):
        from tools.app_session import normalize_index, pick_element_index

        assert normalize_index(-1) == 0
        assert normalize_index(0) == 0
        assert pick_element_index(-1, 5) == 0
        assert pick_element_index(2, 5) == 2
        assert pick_element_index(9, 3) == 2

    @mock.patch("tools.windows.do_list_windows")
    def test_register_launch_result(self, mock_list):
        from tools.app_session import apply_scope_to_launch_result, get_app

        mock_list.return_value = [
            {"title": "Calc", "pid": 42, "hwnd": 100, "process": "calc.exe"},
        ]
        out = apply_scope_to_launch_result(
            {"success": True, "pid": 42, "window_title": "Calc"},
            "calc.exe",
        )
        assert out.get("app_id")
        assert get_app(out["app_id"])["pid"] == 42

    def test_filter_windows_for_app(self):
        from tools.app_session import filter_windows_for_app, register_window

        reg = register_window({"title": "A", "pid": 7, "hwnd": 1, "process": "a.exe"}, set_target=False)
        windows = [
            {"title": "A", "pid": 7, "hwnd": 1},
            {"title": "B", "pid": 8, "hwnd": 2},
        ]
        filtered = filter_windows_for_app(windows, reg["app_id"])
        assert len(filtered) == 1
        assert filtered[0]["pid"] == 7

    def test_resolve_scope_unknown(self):
        from tools.app_session import resolve_scope

        wt, hwnd, err = resolve_scope("missing")
        assert err and "Unknown app_id" in err["error"]

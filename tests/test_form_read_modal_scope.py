"""Tests for form read scope (modal foreground) and role-filtered walk."""
from __future__ import annotations

from unittest import mock


def test_resolve_foreground_owned_modal_same_pid():
    from tools.window_scope import resolve_foreground_owned_modal

    windows = [
        {"hwnd": 100, "title": "App", "class_name": "Notepad", "pid": 42},
        {"hwnd": 200, "title": "Imprimir", "class_name": "#32770", "pid": 42},
    ]
    with mock.patch(
        "awdui_platform.win32_backend.get_foreground_hwnd",
        return_value=200,
    ):
        with mock.patch("tools.windows.do_list_windows", return_value=windows):
            modal = resolve_foreground_owned_modal(parent_pid=42, parent_hwnd=100)
    assert modal is not None
    assert modal["hwnd"] == 200
    assert modal["title"] == "Imprimir"


def test_resolve_foreground_owned_modal_skips_parent():
    from tools.window_scope import resolve_foreground_owned_modal

    windows = [{"hwnd": 100, "title": "App", "class_name": "Notepad", "pid": 42}]
    with mock.patch(
        "awdui_platform.win32_backend.get_foreground_hwnd",
        return_value=100,
    ):
        with mock.patch("tools.windows.do_list_windows", return_value=windows):
            modal = resolve_foreground_owned_modal(parent_pid=42, parent_hwnd=100)
    assert modal is None


def test_resolve_form_read_scope_auto_modal():
    from tools.window_scope import resolve_form_read_scope

    scope_win = {
        "requested_title": "App",
        "resolved_title": "App",
        "scoped": "direct",
        "window": {"hwnd": 100, "pid": 42, "title": "App"},
    }
    modal = {"title": "Imprimir", "hwnd": 200, "class_name": "#32770", "pid": 42}
    with mock.patch("tools.params.resolve_scoped_window", return_value=("App", None, None)):
        with mock.patch("tools.window_scope.resolve_window_scope", return_value=scope_win):
            with mock.patch(
                "tools.window_scope.resolve_foreground_owned_modal",
                return_value=modal,
            ):
                out = resolve_form_read_scope(window_title="App", scope_mode="auto")
    assert out["scope"] == "foreground_modal"
    assert out["window_handle"] == 200
    assert out["window_title"] == "Imprimir"


def test_resolve_form_read_scope_auto_webview2_picker():
    from tools.window_scope import resolve_form_read_scope

    scope_win = {
        "requested_title": "Chat | Teams",
        "resolved_title": "Chat | Teams",
        "scoped": "direct",
        "window": {"hwnd": 100, "pid": 42, "title": "Chat | Teams"},
    }
    modal = {"title": "Abrir", "hwnd": 200, "class_name": "#32770", "pid": 99}
    with mock.patch("tools.params.resolve_scoped_window", return_value=("Chat | Teams", None, None)):
        with mock.patch("tools.window_scope.resolve_window_scope", return_value=scope_win):
            with mock.patch(
                "tools.window_scope.resolve_foreground_owned_modal",
                side_effect=[None, modal],
            ) as fg_mock:
                out = resolve_form_read_scope(window_title="Chat | Teams", scope_mode="auto")
    assert fg_mock.call_count == 2
    assert out["scope"] == "foreground_modal"
    assert out["window_title"] == "Abrir"

    listings = {
        "Edit": {"elements": [{"role": "Edit", "automation_id": "1001", "name": "Copies", "value": "1"}], "backend_used": "uia"},
    }

    def fake_list(**kwargs):
        return listings.get(kwargs.get("role") or "", {"elements": [], "backend_used": "uia"})

    scope = {
        "scope": "foreground_modal",
        "window_title": "Imprimir",
        "window_handle": 200,
        "modal_class": "#32770",
    }
    with mock.patch("tools.window_scope.resolve_form_read_scope", return_value=scope):
        with mock.patch("tools.ui_automation.do_list_elements", side_effect=fake_list):
            from detection.form_read import get_all_values

            payload = get_all_values(window_title="App", scope_mode="auto")
    assert payload["scope"] == "foreground_modal"
    assert "1001" in payload["values"]
    assert "15" not in payload["values"]

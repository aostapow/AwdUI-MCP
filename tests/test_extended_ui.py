"""Tests for tools redistributed from the former extended_ui module."""
from __future__ import annotations

from unittest import mock

import pytest


@pytest.fixture(autouse=True)
def _clear_app_sessions():
    from tools.app_session import clear_apps

    clear_apps()
    yield
    clear_apps()


class TestFuzzyMatch:
    def test_exact_match(self):
        from detection.fuzzy_match import fuzzy_score

        assert fuzzy_score("Save", "Save") == 1.0

    def test_substring_boost(self):
        from detection.fuzzy_match import fuzzy_score

        assert fuzzy_score("Calc", "Calculator") > 0.85

    def test_fuzzy_match_elements(self):
        from detection.fuzzy_match import fuzzy_match_elements

        elems = [
            {"name": "Calculator", "automation_id": "btn1"},
            {"name": "Settings", "automation_id": "btn2"},
        ]
        hits = fuzzy_match_elements(elems, "calcu")
        assert hits and hits[0]["name"] == "Calculator"


class TestSessionAttachTools:
    @mock.patch("tools.windows.do_list_windows")
    def test_attach_to_app(self, mock_list):
        from tools.app_session import get_app
        from tools.session_tools import do_attach_to_app

        mock_list.return_value = [
            {"title": "Calc", "pid": 99, "hwnd": 100, "process": "CalculatorApp.exe"},
        ]
        result = do_attach_to_app("Calculator")
        assert result["success"]
        assert result["app_id"].startswith("app_")
        assert get_app(result["app_id"])["pid"] == 99

    @mock.patch("tools.windows.do_list_windows")
    def test_list_apps(self, _mock_list):
        from tools.app_session import register_window
        from tools.session_tools import do_list_apps

        register_window({"pid": 1, "hwnd": 2, "title": "T", "process": "p.exe"}, set_target=False)
        result = do_list_apps()
        assert result["count"] == 1


class TestUiAutomationExtras:
    def test_get_tree_hash_deterministic(self):
        from tools.ui_automation import do_get_tree_hash

        with mock.patch("tools.ui_automation.do_list_elements") as mock_list:
            mock_list.return_value = {
                "elements": [
                    {"role": "Button", "automation_id": "b1", "name": "OK"},
                    {"role": "Edit", "automation_id": "e1", "name": ""},
                ]
            }
            a = do_get_tree_hash()
            b = do_get_tree_hash()
            assert a["tree_hash"] == b["tree_hash"]
            assert a["element_count"] == 2

    @mock.patch("tools.ui_automation.resolve_scope", return_value=("", 0, None))
    @mock.patch("tools.ui_automation.find_element_for_action")
    @mock.patch("tools.ui_automation._click_coords", return_value=(10, 20))
    @mock.patch("tools.input_tools.do_click")
    def test_right_click_element(self, mock_click, _coords, mock_find, _scope):
        from tools.ui_automation import do_right_click_element

        mock_find.return_value = (
            {"name": "Item", "automation_id": "i1", "x": 10, "y": 20},
            None,
        )
        result = do_right_click_element(name="Item")
        assert result["success"]
        mock_click.assert_called_once_with(10, 20, button="right")

    def test_resolve_scope_unknown_app(self):
        from tools.app_session import resolve_scope

        wt, hwnd, err = resolve_scope("missing")
        assert err and "Unknown app_id" in err["error"]


class TestInputAndVisualExtras:
    @mock.patch("tools.input_tools.do_send_keys")
    def test_press_key(self, mock_send):
        from tools.input_tools import do_press_key

        do_press_key("TAB")
        mock_send.assert_called_once_with("TAB")

    @mock.patch("tools.input_tools.do_send_keys")
    def test_press_key_combo(self, mock_send):
        from tools.input_tools import do_press_key_combo

        do_press_key_combo(["ctrl", "s"])
        mock_send.assert_called_once_with("ctrl+s")

    @mock.patch("tools.visual_diff.compute_visual_diff")
    def test_compare_screenshot_files(self, mock_diff, tmp_path):
        from PIL import Image

        from tools.visual_diff import do_compare_screenshot_files

        p1 = tmp_path / "a.png"
        p2 = tmp_path / "b.png"
        Image.new("RGB", (10, 10), color="red").save(p1)
        Image.new("RGB", (10, 10), color="blue").save(p2)
        mock_diff.return_value = {
            "overlay_b64": "",
            "changed_fraction": 0.5,
            "is_identical": False,
            "bbox": (0, 0, 10, 10),
        }
        result = do_compare_screenshot_files(str(p1), str(p2))
        assert result["success"]
        assert result["changed_fraction"] == 0.5


class TestRegisterCounts:
    def test_session_tools_register_count(self):
        server = mock.MagicMock()
        from tools.session_tools import register

        assert register(server) == 7

    def test_ui_automation_register_count(self):
        server = mock.MagicMock()
        from tools.ui_automation import register

        assert register(server) == 38

"""Tests for UWP / ApplicationFrameHost app identity resolution."""
from __future__ import annotations

import os
import sys
from unittest import mock

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"),
)


class TestTitleAppName:
    def test_strips_suffix_after_dash(self):
        from detection.app_identity import title_app_name

        assert title_app_name("Calculadora - Windows") == "Calculadora"

    def test_empty(self):
        from detection.app_identity import title_app_name

        assert title_app_name("") == ""


class TestRepositoryAppName:
    def test_prefers_app_name_from_framework(self):
        from detection.app_identity import repository_app_name

        app_name, exe_path = repository_app_name(
            {
                "app_name": "CalculatorApp.exe",
                "process_name": "CalculatorApp.exe",
                "exe_path": "C:\\Calc\\CalculatorApp.exe",
            },
            "Calculadora",
        )
        assert app_name == "CalculatorApp.exe"
        assert exe_path == "C:\\Calc\\CalculatorApp.exe"

    def test_uwp_shell_uses_window_title(self):
        from detection.app_identity import repository_app_name

        app_name, exe_path = repository_app_name(
            {
                "app_name": "ApplicationFrameHost.exe",
                "process_name": "ApplicationFrameHost.exe",
                "exe_path": "C:\\Windows\\System32\\ApplicationFrameHost.exe",
                "window_title": "Calculadora",
                "is_uwp_shell": True,
            },
            "Calculadora",
        )
        assert app_name == "Calculadora"
        assert exe_path == ""

    def test_no_more_foreground_fallback(self):
        from detection.app_identity import repository_app_name

        app_name, _ = repository_app_name({}, "Bloc de notas")
        assert app_name == "Bloc de notas"


class TestResolveAppIdentity:
    @mock.patch("detection.app_identity._find_non_shell_window")
    @mock.patch("detection.app_identity._full_exe_path_for_pid")
    @mock.patch("detection.app_identity._pid_for_hwnd")
    @mock.patch("tools.window_classify._get_class_name")
    @mock.patch("tools.window_classify._get_process_name")
    @mock.patch("tools.framework_detect._get_hwnd_for_window")
    def test_uwp_shell_prefers_sibling_process(
        self,
        mock_hwnd,
        mock_proc,
        mock_class,
        mock_pid,
        mock_exe_path,
        mock_sibling,
    ):
        mock_hwnd.return_value = 100
        mock_proc.return_value = "ApplicationFrameHost.exe"
        mock_class.return_value = "ApplicationFrameWindow"
        mock_pid.return_value = 111
        mock_exe_path.return_value = "C:\\Windows\\System32\\ApplicationFrameHost.exe"
        mock_sibling.return_value = {
            "title": "Calculadora",
            "process_name": "CalculatorApp.exe",
            "pid": 222,
        }

        from detection.app_identity import resolve_app_identity

        with mock.patch(
            "detection.app_identity._full_exe_path_for_pid",
            side_effect=lambda pid: (
                "C:\\Calc\\CalculatorApp.exe" if pid == 222 else ""
            ),
        ):
            result = resolve_app_identity("Calculadora", 100)

        assert result["process_name"] == "CalculatorApp.exe"
        assert result["app_name"] == "CalculatorApp.exe"
        assert result["exe_path"] == "C:\\Calc\\CalculatorApp.exe"
        assert result["is_uwp_shell"] is False

    @mock.patch("detection.app_identity._resolve_uwp_core_from_shell")
    @mock.patch("detection.app_identity._find_non_shell_window")
    @mock.patch("detection.app_identity._full_exe_path_for_pid")
    @mock.patch("detection.app_identity._pid_for_hwnd")
    @mock.patch("tools.window_classify._get_class_name")
    @mock.patch("tools.window_classify._get_process_name")
    @mock.patch("tools.framework_detect._get_hwnd_for_window")
    def test_uwp_shell_falls_back_to_title(
        self,
        mock_hwnd,
        mock_proc,
        mock_class,
        mock_pid,
        mock_exe_path,
        mock_sibling,
        mock_core,
    ):
        mock_hwnd.return_value = 100
        mock_proc.return_value = "ApplicationFrameHost.exe"
        mock_class.return_value = "ApplicationFrameWindow"
        mock_pid.return_value = 111
        mock_exe_path.return_value = ""
        mock_core.return_value = ("", "", 0)
        mock_sibling.return_value = {
            "title": "Calculadora",
            "process_name": "ApplicationFrameHost.exe",
            "pid": 111,
        }

        from detection.app_identity import resolve_app_identity

        result = resolve_app_identity("Calculadora", 100)

        assert result["app_name"] == "Calculadora"
        assert result["is_uwp_shell"] is True

    @mock.patch("tools.framework_detect._get_hwnd_for_window")
    def test_no_hwnd_uses_title(self, mock_hwnd):
        mock_hwnd.return_value = 0

        from detection.app_identity import resolve_app_identity

        result = resolve_app_identity("Configuración")
        assert result["app_name"] == "Configuración"

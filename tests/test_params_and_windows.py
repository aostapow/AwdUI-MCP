"""Tests for window title aliases and UWP window selection."""
from __future__ import annotations

import os
import sys

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"),
)

from tools.params import resolve_window_title
from tools.windows import find_matching_window, _best_window_candidate
from detection.orchestrator import DetectionOrchestrator
from detection.element_model import DetectedElement


class TestResolveWindowTitle:
    def test_prefers_window_title(self):
        assert resolve_window_title("Calc", "Notepad") == "Calc"

    def test_falls_back_to_title(self):
        assert resolve_window_title("", "Calc") == "Calc"

    def test_empty(self):
        assert resolve_window_title("", "") is None


class TestFindMatchingWindow:
    def test_prefers_calculator_app_process(self):
        windows = [
            {
                "title": "Calculadora",
                "process_name": "CalculatorApp.exe",
                "x": 0,
                "y": 41,
                "width": 400,
                "height": 625,
            },
            {
                "title": "Calculadora",
                "process_name": "ApplicationFrameHost.exe",
                "x": 50,
                "y": 0,
                "width": 418,
                "height": 675,
            },
        ]
        match = find_matching_window("Calculadora", windows)
        assert match["window"]["process_name"] == "CalculatorApp.exe"

    def test_application_frame_host_when_no_calculator_app(self):
        windows = [
            {
                "title": "Calculadora",
                "process_name": "ApplicationFrameHost.exe",
                "x": 50,
                "y": 0,
                "width": 418,
                "height": 675,
            },
        ]
        match = find_matching_window("Calculadora", windows)
        assert match["window"]["process_name"] == "ApplicationFrameHost.exe"

    def test_best_candidate_skips_minimized(self):
        windows = [
            {"title": "App", "process_name": "a.exe", "x": -32000, "y": -32000, "width": 200, "height": 100},
            {"title": "App", "process_name": "b.exe", "x": 10, "y": 10, "width": 800, "height": 600},
        ]
        best = _best_window_candidate(windows, "app")
        assert best["x"] == 10

    def test_exact_title_beats_substring_in_long_ide_title(self):
        windows = [
            {
                "title": "prueba_screenshot_calculadora.png - Workspace - Cursor",
                "process_name": "Cursor.exe",
                "x": 69,
                "y": 16,
                "width": 1682,
                "height": 1013,
            },
            {
                "title": "Calculadora",
                "process_name": "ApplicationFrameHost.exe",
                "x": 50,
                "y": 0,
                "width": 418,
                "height": 675,
            },
        ]
        match = find_matching_window("Calculadora", windows)
        assert match["window"]["process_name"] == "ApplicationFrameHost.exe"


class TestOrchestratorWeakMsaa:
    def test_weak_uwp_msaa_shell_tree(self):
        elem = DetectedElement(name="Calculadora", role="Role_10", x=0, y=0, width=1, height=1)
        assert DetectionOrchestrator._weak_backend_result("msaa", [elem], "uwp")
        assert not DetectionOrchestrator._weak_backend_result("msaa", [elem], "win32")

    def test_named_button_not_weak(self):
        elem = DetectedElement(
            name="OK", role="Button", x=0, y=0, width=10, height=10, automation_id="btnOk"
        )
        assert not DetectionOrchestrator._weak_backend_result("msaa", [elem], "uwp")

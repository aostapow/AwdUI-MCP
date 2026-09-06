"""UIA window resolution — UWP must attach to CoreWindow HWND."""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"),
)


class TestResolveWindowHandle:
    def test_prefers_calculator_app_hwnd(self):
        from tools.windows import resolve_window_handle, find_matching_window

        windows = [
            {
                "title": "Calculadora",
                "process_name": "CalculatorApp.exe",
                "hwnd": 111,
                "x": 0,
                "y": 1,
                "width": 400,
                "height": 665,
            },
            {
                "title": "Calculadora",
                "process_name": "ApplicationFrameHost.exe",
                "hwnd": 222,
                "x": 43,
                "y": 297,
                "width": 418,
                "height": 675,
            },
        ]
        match = find_matching_window("Calculadora", windows)
        assert match["window"]["hwnd"] == 111

    def test_find_window_uses_hwnd(self, monkeypatch):
        from detection.backends.uia_backend import _find_window

        class FakeDesktop:
            def window(self, handle):
                assert handle == 111
                return f"win-{handle}"

        monkeypatch.setattr(
            "tools.windows.resolve_window_handle",
            lambda _title=None: 111,
        )
        monkeypatch.setattr("tools.target_window.get_target", lambda: "Calculadora")

        result = _find_window(FakeDesktop(), "Calculadora")
        assert result == "win-111"

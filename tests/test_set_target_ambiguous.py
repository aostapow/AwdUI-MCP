"""Ambiguous set_target when multiple same-process windows match."""
from __future__ import annotations

import os
import sys

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"),
)


class TestSetTargetAmbiguous:
    def setup_method(self):
        from tools import target_window

        target_window._target_window = None
        target_window._target_hwnd = None
        target_window._focus_policy = "minimal"

    def test_two_notepad_instances_ambiguous(self):
        from tools.windows import find_matching_window

        windows = [
            {
                "title": "Sin título: Bloc de notas",
                "hwnd": 1001,
                "pid": 10,
                "process_name": "notepad.exe",
                "x": 0,
                "y": 0,
                "width": 800,
                "height": 600,
            },
            {
                "title": "Sin título: Bloc de notas",
                "hwnd": 1002,
                "pid": 20,
                "process_name": "notepad.exe",
                "x": 50,
                "y": 50,
                "width": 800,
                "height": 600,
            },
        ]
        result = find_matching_window("Bloc de notas", windows)
        assert result.get("window") is None
        assert result.get("ambiguous") is True
        assert len(result.get("candidates") or []) == 2

    def test_window_handle_pins_target(self):
        from tools.target_window import get_target, get_target_hwnd, set_target

        set_target(None, window_handle=4242)
        assert get_target_hwnd() == 4242

    @staticmethod
    def _mock_windows():
        return [
            {
                "title": "Sin título: Bloc de notas",
                "hwnd": 1001,
                "pid": 10,
                "process_name": "notepad.exe",
                "x": 0,
                "y": 0,
                "width": 800,
                "height": 600,
            },
            {
                "title": "Sin título: Bloc de notas",
                "hwnd": 1002,
                "pid": 20,
                "process_name": "notepad.exe",
                "x": 50,
                "y": 50,
                "width": 800,
                "height": 600,
            },
        ]

    def test_disambiguate_last_set(self):
        from tools.windows import find_matching_window

        result = find_matching_window(
            "Bloc de notas",
            self._mock_windows(),
            disambiguate="last_set",
            preferred_hwnd=1002,
        )
        assert result.get("window") is not None
        assert result["window"]["hwnd"] == 1002

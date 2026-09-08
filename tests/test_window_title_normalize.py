"""Window title normalization for multi-instance matching."""
from __future__ import annotations

import os
import sys

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"),
)


class TestWindowTitleNormalize:
    def test_dirty_asterisk_stripped(self):
        from tools.windows import (
            _normalize_window_title_for_match,
            _title_matches_query,
        )

        dirty = "*Sin título: Bloc de notas"
        clean = "Sin título: Bloc de notas"
        assert _normalize_window_title_for_match(dirty) == _normalize_window_title_for_match(clean)
        assert _title_matches_query(dirty, clean)
        assert _title_matches_query(clean, "Bloc de notas")

    def test_find_matching_window_dirty_matches_clean_hint(self):
        from tools.windows import find_matching_window

        windows = [
            {
                "title": "*Sin título: Bloc de notas",
                "hwnd": 111,
                "pid": 100,
                "process_name": "notepad.exe",
                "x": 0,
                "y": 0,
                "width": 800,
                "height": 600,
            },
            {
                "title": "doc.txt: Bloc de notas",
                "hwnd": 222,
                "pid": 200,
                "process_name": "notepad.exe",
                "x": 10,
                "y": 10,
                "width": 800,
                "height": 600,
            },
        ]
        result = find_matching_window("Sin título: Bloc de notas", windows)
        assert result.get("window") is not None
        assert result["window"]["hwnd"] == 111

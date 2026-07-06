"""Tests for element coordinate normalization."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"))


class TestElementCoords:
    def test_window_relative_to_screen(self, monkeypatch):
        from detection.element_coords import to_screen_coords

        monkeypatch.setattr(
            "detection.element_coords.window_region",
            lambda _t: {"x": 149, "y": 126, "w": 418, "h": 675},
        )
        elem = {"x": 287, "y": 473, "width": 77, "height": 50, "name": "Seis"}
        out = to_screen_coords(elem, "Calculadora")
        assert out["x"] == 436
        assert out["y"] == 599
        assert out["clickable_x"] == 474
        assert out["clickable_y"] == 624

    def test_click_coords_uses_screen_center(self, monkeypatch):
        from detection.element_coords import click_coords

        monkeypatch.setattr(
            "detection.element_coords.window_region",
            lambda _t: {"x": 149, "y": 126, "w": 418, "h": 675},
        )
        elem = {"x": 287, "y": 473, "width": 77, "height": 50}
        assert click_coords(elem, "Calculadora") == (474, 624)

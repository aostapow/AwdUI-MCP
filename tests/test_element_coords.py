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

    def test_screen_bbox_after_dpi_scale(self, monkeypatch):
        from detection.element_coords import screen_bbox

        monkeypatch.setattr(
            "detection.element_coords.window_region",
            lambda _t: {"x": 100, "y": 100, "w": 500, "h": 500},
        )
        monkeypatch.setattr("detection.element_coords._dpi_scale_for", lambda _t: 1.25)
        monkeypatch.setattr(
            "tools.screenshot.logical_to_physical",
            lambda x, y, scale: (int(x * scale), int(y * scale)),
        )
        # Logical coords outside the physical window region get scaled.
        elem = {"x": 1000, "y": 1000, "width": 77, "height": 51}
        assert screen_bbox(elem, "App") == (1250, 1250, 96, 63)

    def test_bottom_row_logical_window_relative_at_dpi(self, monkeypatch):
        from detection.element_coords import to_screen_coords

        monkeypatch.setattr(
            "detection.element_coords.window_region",
            lambda _t: {"x": 149, "y": 126, "w": 418, "h": 675},
        )
        monkeypatch.setattr("detection.element_coords._dpi_scale_for", lambda _t: 1.25)
        monkeypatch.setattr(
            "tools.screenshot.logical_to_physical",
            lambda x, y, scale: (int(x * scale), int(y * scale)),
        )
        elem = {"x": 130, "y": 525, "width": 77, "height": 51, "name": "Uno"}
        out = to_screen_coords(elem, "Calculadora")
        assert out["x"] == 311
        assert out["y"] == 782
        assert out["width"] == 96
        assert out["height"] == 63

    def test_physical_window_relative_no_extra_scale(self, monkeypatch):
        from detection.element_coords import to_screen_coords

        monkeypatch.setattr(
            "detection.element_coords.window_region",
            lambda _t: {"x": 149, "y": 126, "w": 418, "h": 675},
        )
        monkeypatch.setattr("detection.element_coords._dpi_scale_for", lambda _t: 1.25)
        elem = {"x": 287, "y": 473, "width": 77, "height": 50, "name": "Seis"}
        out = to_screen_coords(elem, "Calculadora")
        assert out["x"] == 436
        assert out["y"] == 599
        assert out["width"] == 77
        assert out["height"] == 50

    def test_screen_coords_left_unchanged(self, monkeypatch):
        from detection.element_coords import to_screen_coords

        monkeypatch.setattr(
            "detection.element_coords.window_region",
            lambda _t: {"x": 149, "y": 126, "w": 418, "h": 675},
        )
        elem = {"x": 436, "y": 599, "width": 77, "height": 50}
        out = to_screen_coords(elem, "Calculadora")
        assert out["x"] == 436
        assert out["y"] == 599

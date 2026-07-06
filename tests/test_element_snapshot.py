"""Tests for element-only repository screenshots."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"))


class TestElementSnapshot:
    def test_capture_element_crop_saves_png(self, tmp_path, monkeypatch):
        from detection import repo_store
        from detection.object_snapshot import capture_element_crop
        from PIL import Image

        assets = tmp_path / "assets"
        monkeypatch.setattr(repo_store, "_ASSETS_DIR", assets)

        fake = Image.new("RGB", (200, 200), color=(80, 120, 200))
        crop = fake.crop((10, 20, 40, 60))
        monkeypatch.setattr(
            "detection.object_snapshot._capture_element_image",
            lambda elem, window_title=None, repo_path=None: (crop, (10, 20, 30, 40)),
        )

        elem = {"x": 10, "y": 20, "width": 30, "height": 40, "name": "Seis"}
        out = capture_element_crop(elem, repo_path="Calculadora/num6Button", app_id="testapp")
        assert out is not None
        crop_rel = out["latest"]["images"]["crop"]
        assert crop_rel == "testapp/Calculadora_num6Button_crop.png"
        png = assets / "testapp" / "Calculadora_num6Button_crop.png"
        assert png.is_file()
        img = Image.open(png)
        assert img.size == (30, 40)

    def test_no_bbox_returns_none(self, tmp_path, monkeypatch):
        from detection import repo_store
        from detection.object_snapshot import capture_element_crop

        monkeypatch.setattr(repo_store, "_ASSETS_DIR", tmp_path / "assets")
        assert capture_element_crop({"name": "x"}, repo_path="w/o", app_id="a") is None

    def test_is_window_relative(self):
        from detection.object_snapshot import _is_window_relative

        region = {"x": 100, "y": 50, "w": 400, "h": 600}
        assert _is_window_relative((287, 473, 77, 50), region)
        assert not _is_window_relative((1200, 473, 77, 50), region)

    def test_bbox_candidates_window_relative_to_screen(self, monkeypatch):
        from detection.object_snapshot import _bbox_candidates

        monkeypatch.setattr(
            "detection.object_snapshot._window_region",
            lambda _t: {"x": 149, "y": 126, "w": 418, "h": 675},
        )
        cands = _bbox_candidates({"x": 287, "y": 473, "width": 77, "height": 50}, window_title="Calc")
        assert cands == [(436, 599, 77, 50)]

    def test_verify_crop_rejects_wrong_element(self, monkeypatch):
        from detection.object_snapshot import _verify_crop
        from PIL import Image

        crop = Image.new("RGB", (40, 40), color=(200, 200, 200))
        monkeypatch.setattr("tools.spy_bridge.spy_available", lambda: True)
        monkeypatch.setattr(
            "tools.spy_bridge.spy_inspect_at",
            lambda x, y: {"found": True, "properties": {"automation_id": "xSquaredButton", "name": "x²"}},
        )
        ok = _verify_crop(crop, (10, 10, 40, 40), "num6Button", "Seis")
        assert ok is False

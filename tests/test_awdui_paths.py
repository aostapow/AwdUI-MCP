"""Tests for runtime path helpers."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"))


def test_diagnostics_under_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AWDUI_DATA", str(tmp_path))
    import importlib
    import awdui_paths as mod

    importlib.reload(mod)
    path = mod.diagnostics_dir()
    assert path.is_dir()
    assert path.parent == tmp_path


def test_screenshots_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AWDUI_DATA", str(tmp_path))
    import importlib
    import awdui_paths as mod

    importlib.reload(mod)
    path = mod.screenshots_dir()
    assert path.is_dir()
    assert path.name == "screenshots"

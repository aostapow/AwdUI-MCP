"""Tests for performance mode toggles."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"))


class TestPerf:
    def test_fast_by_default(self, monkeypatch):
        monkeypatch.delenv("AWDUI_VERIFY", raising=False)
        from tools import perf
        assert perf.is_fast_mode()
        assert not perf.verify_visual_changes()

    def test_verify_env(self, monkeypatch):
        monkeypatch.setenv("AWDUI_VERIFY", "1")
        from importlib import reload
        import tools.perf as perf
        reload(perf)
        assert not perf.is_fast_mode()
        assert perf.verify_visual_changes()

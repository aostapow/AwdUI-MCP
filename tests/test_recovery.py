"""Unit tests for recovery helpers."""
import os
import sys
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestDetectBlockers:
    @mock.patch("tools.windows.do_list_windows")
    def test_detects_error_dialog(self, mock_list):
        mock_list.return_value = [
            {"title": "Calculadora", "process_name": "CalculatorApp.exe"},
            {"title": "Error de actualización", "process_name": "svchost.exe"},
        ]
        from tests.integration.recovery import detect_blockers

        blockers = detect_blockers("Calculadora")
        assert len(blockers) >= 1
        assert any("error" in b["title"].lower() for b in blockers)


class TestWithStepRecovery:
    @mock.patch("tests.integration.recovery.attempt_recovery", return_value=True)
    def test_retries_after_failure(self, _rec):
        calls = {"n": 0}

        def fn():
            calls["n"] += 1
            if calls["n"] < 2:
                raise RuntimeError("transient")
            return "ok"

        from tests.integration.recovery import with_step_recovery

        assert with_step_recovery(fn, ctx={"window_title": "Calc"}) == "ok"
        assert calls["n"] == 2

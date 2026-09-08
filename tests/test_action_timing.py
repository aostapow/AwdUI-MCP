"""Tests for action timing helpers."""
from __future__ import annotations

from unittest import mock

from tools.action_timing import (
    ActionTimer,
    classify_performance,
    format_timing_suffix,
    format_verify_suffix,
    run_post_act_verify,
)


class TestActionTimer:
    def test_attach_phases_and_total(self):
        timer = ActionTimer()
        timer.mark("find_ms", 120)
        timer.mark("act_ms", 80)
        result = timer.attach({"success": True})
        assert result["elapsed_ms"] == 200
        assert result["timing"]["operational_ms"] == 200
        assert result["timing"]["find_ms"] == 120
        assert result["timing"]["act_ms"] == 80
        assert result["performance"] == "fast"


class TestClassifyPerformance:
    def test_buckets(self):
        assert classify_performance(200) == "fast"
        assert classify_performance(800) == "ok"
        assert classify_performance(4000) == "slow"


class TestFormatTimingSuffix:
    def test_phased(self):
        text = format_timing_suffix(
            {
                "elapsed_ms": 412,
                "timing": {"find_ms": 180, "act_ms": 95, "verify_ms": 137, "total_ms": 412},
                "performance": "ok",
            }
        )
        assert "total 412ms" in text
        assert "find 180ms" in text
        assert "verify 137ms" in text

    def test_slow_flag(self):
        text = format_timing_suffix({"elapsed_ms": 5000, "timing": {"total_ms": 5000}, "performance": "slow"})
        assert "SLOW" in text


class TestVerify:
    def test_run_post_act_verify_name(self):
        with mock.patch(
            "tools.wait_tools.do_wait_for_condition",
            return_value={
                "success": True,
                "actual": "Cerrar control flotante de historial",
                "attempts": 2,
                "elapsed_ms": 150,
            },
        ) as wait_mock:
            v = run_post_act_verify(
                window_title="Calculadora",
                verify_automation_id="HistoryButton",
                verify_name_contains="Cerrar",
            )
        assert v["verified"] is True
        assert v["verify_ms"] >= 0
        wait_mock.assert_called_once()
        assert wait_mock.call_args.kwargs["expected_value"] == "Cerrar"

    def test_run_post_act_verify_delegates_wait_params(self):
        with mock.patch(
            "tools.wait_tools.do_wait_for_condition",
            return_value={
                "success": True,
                "actual": "Se muestra 7",
                "attempts": 3,
                "elapsed_ms": 280,
            },
        ) as wait_mock:
            v = run_post_act_verify(
                window_title="Calculadora",
                verify_automation_id="CalculatorResults",
                verify_name_contains="Se muestra 7",
                timeout_ms=2000,
                poll_ms=50,
            )
        assert v["verified"] is True
        assert v["verify_name"] == "Se muestra 7"
        wait_mock.assert_called_once()
        assert wait_mock.call_args.kwargs["timeout_ms"] == 2000
        assert wait_mock.call_args.kwargs["poll_ms"] == 50

    def test_format_verify_suffix(self):
        assert "verified" in format_verify_suffix({"verified": True})
        assert "failed" in format_verify_suffix({"verified": False, "verify_error": "x"})


class TestDoFindElementTiming:
    def test_find_element_includes_elapsed(self, monkeypatch):
        from tools.ui_automation import do_find_element

        monkeypatch.setattr(
            "tools.ui_automation._orch",
            lambda: mock.Mock(
                find_elements=lambda **kwargs: {
                    "found": True,
                    "elements": [{"name": "A", "role": "Button", "x": 1, "y": 2, "width": 3, "height": 4}],
                    "backend_used": "uia",
                }
            ),
        )
        monkeypatch.setattr(
            "detection.repo_lookup.resolve_via_repository",
            lambda *a, **k: None,
        )
        monkeypatch.setattr(
            "detection.element_coords.to_screen_coords",
            lambda e, wt: e,
        )
        out = do_find_element(automation_id="btn", window_title="App")
        assert "elapsed_ms" in out
        assert out["timing"]["find_ms"] == out["elapsed_ms"]

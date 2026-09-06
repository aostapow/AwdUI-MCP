"""Unit tests for evidence helpers (mocked UIA/OCR)."""
import os
import sys
from unittest import mock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestEvidenceNormalize:
    def test_normalize_number_strips_spaces(self):
        from tests.integration.evidence import _normalize_number
        assert _normalize_number("1 05") == "105"


class TestCalculatorDisplayParse:
    def test_spanish_se_muestra(self):
        from tests.integration.calculator_harness import _extract_numeric
        assert _extract_numeric("Se muestra 42") == "42"

    def test_english_display_is(self):
        from tests.integration.calculator_harness import _extract_numeric
        assert _extract_numeric("Display is 4") == "4"


class TestAssertDisplayEquals:
    @mock.patch("tests.integration.evidence.write_run_log")
    @mock.patch("tests.integration.evidence.read_display_with_fallback")
    @mock.patch("tests.integration.calculator_harness.resolve_window_title", return_value="Calculadora")
    def test_uia_match_passes(self, _title, mock_read, _log):
        mock_read.return_value = {"value": "4", "source": "uia", "screenshot_path": ""}
        from tests.integration.evidence import assert_display_equals

        out = assert_display_equals("4", ticket_id="T-test")
        assert out["ok"] is True
        assert out["actual"] == "4"
        assert out["source"] == "uia"

    @mock.patch("tests.integration.evidence.capture_evidence", return_value="/tmp/mismatch.png")
    @mock.patch("tests.integration.evidence.write_run_log")
    @mock.patch("tests.integration.evidence.read_display_with_fallback")
    @mock.patch("tests.integration.calculator_harness.resolve_window_title", return_value="Calculadora")
    def test_mismatch_fails_with_screenshot(self, _title, mock_read, _log, _cap):
        mock_read.return_value = {"value": "5", "source": "uia", "screenshot_path": ""}
        from tests.integration.evidence import assert_display_equals

        with pytest.raises(AssertionError, match="mismatch|expected"):
            assert_display_equals("4", ticket_id="T-fail")

    @mock.patch("tests.integration.evidence.capture_evidence", return_value="/tmp/empty.png")
    @mock.patch("tests.integration.evidence.write_run_log")
    @mock.patch("tests.integration.evidence.read_display_with_fallback")
    @mock.patch("tests.integration.calculator_harness.resolve_window_title", return_value="Calculadora")
    def test_empty_display_fails(self, _title, mock_read, _log, _cap):
        mock_read.return_value = {"value": "", "source": "none", "screenshot_path": ""}
        from tests.integration.evidence import assert_display_equals

        with pytest.raises(AssertionError, match="could not read display"):
            assert_display_equals("4", ticket_id="T-empty")

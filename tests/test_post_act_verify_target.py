"""Tests for verify target resolution via repo agent_hints."""
from __future__ import annotations

from unittest import mock

from tools.ui_automation import _finish_action_with_verify, _resolve_verify_target
from tools.action_timing import ActionTimer


class TestResolveVerifyTarget:
    def test_explicit_verify_automation_id_wins(self):
        assert _resolve_verify_target(
            "equalButton",
            "Foo",
            "7",
            "Calculadora",
        ) == "Foo"

    def test_repo_hint_redirects_when_display_live(self):
        with mock.patch(
            "detection.repo_store.get_hints_by_automation_id",
            return_value="verify_automation_id: DisplayResults\n",
        ), mock.patch(
            "tools.spy_bridge.spy_available",
            return_value=True,
        ), mock.patch(
            "tools.spy_bridge.spy_verify_live",
            return_value={"live": True},
        ):
            target = _resolve_verify_target(
                "equalButton",
                None,
                "7",
                "MyApp",
            )
        assert target == "DisplayResults"

    def test_no_redirect_without_name_needle(self):
        assert _resolve_verify_target("equalButton", None, None, "MyApp") == "equalButton"

    def test_no_redirect_when_display_not_live(self):
        with mock.patch(
            "detection.repo_store.get_hints_by_automation_id",
            return_value="verify_automation_id: DisplayResults\n",
        ), mock.patch(
            "tools.spy_bridge.spy_available",
            return_value=True,
        ), mock.patch(
            "tools.spy_bridge.spy_verify_live",
            return_value={"live": False},
        ):
            target = _resolve_verify_target(
                "equalButton",
                None,
                "7",
                "MyApp",
            )
        assert target == "equalButton"


class TestFinishActionWithVerify:
    def test_verify_uses_repo_hint_target(self):
        timer = ActionTimer()
        with mock.patch(
            "detection.repo_store.get_hints_by_automation_id",
            return_value="verify_automation_id: DisplayResults\n",
        ), mock.patch(
            "tools.spy_bridge.spy_available",
            return_value=True,
        ), mock.patch(
            "tools.spy_bridge.spy_verify_live",
            return_value={"live": True},
        ), mock.patch(
            "tools.wait_tools.do_wait_for_condition",
            return_value={
                "success": True,
                "actual": "Shows 7",
                "attempts": 1,
            },
        ) as wait_mock:
            out = _finish_action_with_verify(
                timer,
                {"success": True, "element": {"automation_id": "equalButton"}},
                window_title="MyApp",
                verify_automation_id=None,
                verify_name_contains="7",
                acted_automation_id="equalButton",
            )
        assert out["verified"] is True
        wait_mock.assert_called_once()
        assert wait_mock.call_args.kwargs.get("automation_id") == "DisplayResults"

    def test_verify_failure_includes_generic_hint(self):
        timer = ActionTimer()
        with mock.patch(
            "detection.repo_store.get_hints_by_automation_id",
            return_value="",
        ), mock.patch(
            "tools.spy_bridge.spy_available",
            return_value=True,
        ), mock.patch(
            "tools.spy_bridge.spy_verify_live",
            return_value={"live": False},
        ), mock.patch(
            "tools.wait_tools.do_wait_for_condition",
            return_value={
                "success": False,
                "actual": "Equals",
                "error": "timeout",
                "attempts": 3,
            },
        ):
            out = _finish_action_with_verify(
                timer,
                {"success": True, "element": {"automation_id": "equalButton"}},
                window_title="MyApp",
                verify_automation_id=None,
                verify_name_contains="7",
                acted_automation_id="equalButton",
            )
        assert out["verified"] is False
        assert out.get("verify_target_used") == "equalButton"
        assert "repo agent_hints" in out.get("hint", "")

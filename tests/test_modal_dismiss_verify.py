"""Post-act verify: modal dismissed via list_windows poll."""
from __future__ import annotations

from unittest import mock

from tools.action_timing import run_post_act_verify, format_verify_suffix
from tools.ui_automation import _finish_action_with_verify
from tools.action_timing import ActionTimer


class TestModalDismissVerify:
    def test_modal_dismissed_when_title_absent(self):
        with mock.patch(
            "tools.window_scope.modal_title_visible",
            side_effect=[True, False],
        ):
            v = run_post_act_verify(
                window_title="Buscar",
                verify_modal_dismissed=True,
                modal_title="Buscar",
                parent_pid=1234,
                timeout_ms=500,
                poll_ms=50,
            )
        assert v["verified"] is True
        assert v.get("modal_dismissed") is True

    def test_modal_still_open_returns_failure(self):
        with mock.patch(
            "tools.window_scope.modal_title_visible",
            return_value=True,
        ):
            v = run_post_act_verify(
                verify_modal_dismissed=True,
                modal_title="Guardar como",
                timeout_ms=200,
                poll_ms=50,
            )
        assert v["verified"] is False
        assert v.get("modal_still_open") == "Guardar como"
        assert "modal still" in v.get("verify_error", "")

    def test_format_verify_suffix_modal_dismissed(self):
        assert "modal dismissed" in format_verify_suffix({"modal_dismissed": True})

    def test_finish_action_with_verify_modal_dismiss(self):
        timer = ActionTimer()
        with mock.patch(
            "tools.window_scope.modal_title_visible",
            return_value=False,
        ):
            out = _finish_action_with_verify(
                timer,
                {"success": True, "element": {"name": "Cancelar", "role": "Button"}},
                window_title="Buscar",
                verify_automation_id=None,
                verify_name_contains=None,
                verify_modal_dismissed=True,
                modal_title="Buscar",
                parent_pid=999,
            )
        assert out["verified"] is True
        assert out.get("modal_dismissed") is True

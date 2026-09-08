"""Tests for click/invoke scope_mode auto modal resolution."""
from __future__ import annotations

from unittest import mock


def test_do_click_element_scopes_to_foreground_modal():
    scope = {
        "scope": "foreground_modal",
        "window_title": "Abrir",
        "window_handle": 999,
        "parent_title": "Chat | Teams",
    }
    find_calls = []

    def fake_find(**kwargs):
        find_calls.append(kwargs)
        return {
            "found": True,
            "elements": [{
                "role": "Button",
                "name": "Cancelar",
                "automation_id": "2",
                "patterns": ["Invoke"],
            }],
            "backend_used": "uia",
        }

    invoke_result = {"success": True, "method": "InvokePattern"}

    with mock.patch(
        "tools.ui_automation._apply_action_scope",
        return_value=("Abrir", 999, scope),
    ):
        with mock.patch("tools.ui_automation.do_find_element", side_effect=fake_find):
            with mock.patch(
                "tools.ui_automation._try_invoke_click",
                return_value=invoke_result,
            ):
                with mock.patch(
                    "tools.ui_automation._finish_action_with_verify",
                    side_effect=lambda _t, r, **kw: {**r, "verified": True, **kw},
                ):
                    from tools.ui_automation import do_click_element

                    out = do_click_element(
                        name="Cancelar",
                        role="Button",
                        verify_modal_dismissed=True,
                        scope_mode="auto",
                    )

    assert out["success"] is True
    assert find_calls[0]["window_title"] == "Abrir"
    assert find_calls[0]["window_handle"] == 999


def test_enrich_modal_verify_kwargs_sets_modal_title():
    from tools.ui_automation import _enrich_modal_verify_kwargs

    verify_kwargs = {"verify_modal_dismissed": True, "modal_title": None, "parent_pid": None}
    scope = {
        "scope": "foreground_modal",
        "window_title": "Abrir",
        "parent_title": "Chat | Teams",
    }
    with mock.patch("tools.ui_automation._resolve_parent_pid", return_value=42):
        _enrich_modal_verify_kwargs(verify_kwargs, scope, window_title="Abrir")
    assert verify_kwargs["modal_title"] == "Abrir"
    assert verify_kwargs["parent_pid"] == 42

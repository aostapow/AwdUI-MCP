"""Tests for SelectionItem post-act verify (UWP NavView / radio groups)."""
from __future__ import annotations

from unittest import mock

from tools.action_timing import (
    _contact_needles_from_acted_name,
    run_selection_item_verify,
    snapshot_header_name,
    snapshot_selection_prestate,
)


class TestContactNeedles:
    def test_teams_treeitem_name(self):
        needles = _contact_needles_from_acted_name(
            "Chat Awamori, Nicolas sin leer 1 mensaje"
        )
        assert "Awamori" in needles
        assert any("Nicolas" in n or "Awamori" in n for n in needles)

    def test_strips_chat_prefix(self):
        needles = _contact_needles_from_acted_name("Chat Awamori, Nicolas")
        assert needles[0].startswith("Awamori")


class TestSnapshotHeaderName:
    def test_reads_header_automation_id(self):
        with mock.patch(
            "tools.wait_tools._read_properties",
            return_value={"name": "Estándar"},
        ) as read_mock:
            name = snapshot_header_name("Calculadora")
        assert name == "Estándar"
        read_mock.assert_called_once_with(
            automation_id="Header", window_title="Calculadora"
        )


class TestSnapshotSelectionPrestate:
    def test_captures_header_and_window_title(self):
        with mock.patch(
            "tools.action_timing.snapshot_header_name",
            return_value="Estándar",
        ), mock.patch(
            "tools.target_window.get_target",
            return_value="Calculadora",
        ):
            pre = snapshot_selection_prestate("Calculadora")
        assert pre["header_name"] == "Estándar"
        assert pre["window_title"] == "Calculadora"


class TestRunSelectionItemVerify:
    def test_header_changed_passes_fast(self):
        calls = {"n": 0}

        def _read(**kwargs):
            calls["n"] += 1
            if kwargs.get("automation_id") == "Header":
                if calls["n"] == 1:
                    return {"name": "Científica"}
                return {"name": "Científica"}
            return None

        with mock.patch("tools.wait_tools._read_properties", side_effect=_read):
            v = run_selection_item_verify(
                window_title="Calculadora",
                acted_automation_id="ScientificItem",
                pre_header_name="Estándar",
                timeout_ms=500,
                poll_ms=10,
            )
        assert v["verified"] is True
        assert v["verify_method"] == "Header.changed"
        assert v["verify_ms"] < 500

    def test_selection_item_is_selected(self):
        with mock.patch(
            "tools.wait_tools._read_properties",
            return_value={
                "name": "Oscuro",
                "patterns": {"SelectionItem": {"value": True}},
            },
        ):
            v = run_selection_item_verify(
                window_title="Calculadora",
                acted_automation_id="DarkThemeRadioButton",
                acted_role="RadioButton",
                timeout_ms=500,
                poll_ms=10,
            )
        assert v["verified"] is True
        assert v["verify_method"] == "SelectionItem.is_selected"

    def test_window_title_contact_for_treeitem(self):
        with mock.patch(
            "tools.action_timing._current_window_title",
            return_value="Chat | Awamori, Nicolas | Microsoft Teams",
        ):
            v = run_selection_item_verify(
                window_title="Chat | Microsoft Teams",
                acted_automation_id="menur20",
                acted_name="Chat Awamori, Nicolas",
                acted_role="TreeItem",
                pre_window_title="Chat | Microsoft Teams",
                timeout_ms=500,
                poll_ms=10,
            )
        assert v["verified"] is True
        assert v["verify_method"] == "WindowTitle.contact"
        assert "Awamori" in v["verify_name"]

    def test_chat_context_compose_ready(self):
        read = mock.Mock(return_value=None)

        with mock.patch(
            "tools.action_timing._current_window_title",
            return_value="Chat | Awamori, Nicolas | Microsoft Teams",
        ), mock.patch("tools.wait_tools._read_properties", read):
            v = run_selection_item_verify(
                window_title="Chat | Awamori, Nicolas | Microsoft Teams",
                acted_automation_id="menur20",
                acted_name="Chat Awamori, Nicolas",
                acted_role="TreeItem",
                pre_window_title="Chat | Awamori, Nicolas | Microsoft Teams",
                timeout_ms=80,
                poll_ms=10,
            )
        assert v["verified"] is True
        assert v["verify_method"] == "WindowTitle.stable"
        read.assert_not_called()

    def test_treeitem_any_title_change(self):
        titles = iter(
            [
                "Chat | Awamori, Nicolas | Microsoft Teams",
                "Chat | Awamori, Nicolas | Microsoft Teams",
                "Chat | Testing Argentina | Microsoft Teams",
            ]
        )

        with mock.patch(
            "tools.action_timing._current_window_title",
            side_effect=lambda *_a, **_k: next(
                titles, "Chat | Testing Argentina | Microsoft Teams"
            ),
        ), mock.patch("tools.wait_tools._read_properties") as read, mock.patch(
            "tools.action_timing.time.sleep",
            lambda *_a, **_k: None,
        ):
            v = run_selection_item_verify(
                window_title="Chat | Awamori, Nicolas | Microsoft Teams",
                acted_automation_id="menur1oo",
                acted_name="Chat de grupo Testing Argentina",
                acted_role="TreeItem",
                pre_window_title="Chat | Awamori, Nicolas | Microsoft Teams",
                timeout_ms=500,
                poll_ms=10,
            )
        assert v["verified"] is True
        assert v["verify_method"] in ("WindowTitle.changed", "WindowTitle.contact")
        read.assert_not_called()

    def test_treeitem_stable_reselect_same_chat(self):
        with mock.patch(
            "tools.action_timing._current_window_title",
            return_value="Chat | Awamori, Nicolas | Microsoft Teams",
        ), mock.patch("tools.wait_tools._read_properties") as read:
            v = run_selection_item_verify(
                window_title="Chat | Awamori, Nicolas | Microsoft Teams",
                acted_automation_id="menur1oc",
                acted_name="Chat Awamori, Nicolas",
                acted_role="TreeItem",
                pre_window_title="Chat | Awamori, Nicolas | Microsoft Teams",
                timeout_ms=500,
                poll_ms=10,
            )
        assert v["verified"] is True
        assert v["verify_method"] == "WindowTitle.stable"
        assert v["verify_ms"] < 50
        read.assert_not_called()

    def test_treeitem_title_poll_no_uia_until_deadline(self):
        titles = iter(
            [
                "Chat | Microsoft Teams",
                "Chat | Microsoft Teams",
                "Chat | Awamori, Nicolas | Microsoft Teams",
            ]
        )
        read = mock.Mock(return_value=None)

        with mock.patch(
            "tools.action_timing._current_window_title",
            side_effect=lambda *_a, **_k: next(titles, "Chat | Awamori, Nicolas | Microsoft Teams"),
        ), mock.patch("tools.wait_tools._read_properties", read), mock.patch(
            "tools.action_timing.time.sleep",
            lambda *_a, **_k: None,
        ):
            v = run_selection_item_verify(
                window_title="Chat | Microsoft Teams",
                acted_automation_id="menurq9",
                acted_name="Chat Awamori, Nicolas",
                acted_role="TreeItem",
                pre_window_title="Chat | Microsoft Teams",
                timeout_ms=500,
                poll_ms=10,
            )
        assert v["verified"] is True
        assert v["verify_method"] in ("WindowTitle.contact", "WindowTitle.changed")
        read.assert_not_called()

    def test_timeout_when_unchanged(self):
        with mock.patch(
            "tools.wait_tools._read_properties",
            return_value={"name": "Estándar"},
        ):
            v = run_selection_item_verify(
                window_title="Calculadora",
                acted_automation_id="ScientificItem",
                pre_header_name="Estándar",
                timeout_ms=120,
                poll_ms=40,
            )
        assert v["verified"] is False
        assert "unchanged" in v["verify_error"]


class TestFinishActionSelectionVerify:
    def test_invoke_selection_item_uses_header_verify(self):
        from tools.action_timing import ActionTimer
        from tools.ui_automation import _finish_action_with_verify

        timer = ActionTimer()
        with mock.patch(
            "tools.action_timing.run_selection_item_verify",
            return_value={
                "verified": True,
                "verify_ms": 95,
                "verify_method": "Header.changed",
                "verify_name": "Científica",
            },
        ) as sel_mock:
            out = _finish_action_with_verify(
                timer,
                {
                    "success": True,
                    "method": "SelectionItem",
                    "element": {
                        "automation_id": "ScientificItem",
                        "name": "Científica",
                        "role": "ListItem",
                    },
                    "pre_header_name": "Estándar",
                },
                window_title="Calculadora",
                verify_automation_id=None,
                verify_name_contains=None,
                acted_automation_id="ScientificItem",
            )
        sel_mock.assert_called_once()
        assert out["verified"] is True
        assert out["verify_method"] == "Header.changed"
        assert out["timing"]["verify_ms"] == 95

    def test_invoke_treeitem_uses_selection_verify(self):
        from tools.action_timing import ActionTimer
        from tools.ui_automation import _finish_action_with_verify

        timer = ActionTimer()
        with mock.patch(
            "tools.action_timing.run_selection_item_verify",
            return_value={
                "verified": True,
                "verify_ms": 42,
                "verify_method": "WindowTitle.contact",
                "verify_name": "Chat | Awamori, Nicolas | Microsoft Teams",
            },
        ) as sel_mock:
            out = _finish_action_with_verify(
                timer,
                {
                    "success": True,
                    "method": "InvokePattern",
                    "element": {
                        "automation_id": "menurq9",
                        "name": "Chat Awamori, Nicolas Sin conexión",
                        "role": "TreeItem",
                    },
                    "pre_window_title": "Chat | Microsoft Teams",
                },
                window_title="Chat | Microsoft Teams",
                verify_automation_id=None,
                verify_name_contains=None,
                acted_automation_id="menurq9",
            )
        sel_mock.assert_called_once()
        assert out["verified"] is True
        assert out["verify_method"] == "WindowTitle.contact"

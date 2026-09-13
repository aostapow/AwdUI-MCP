"""Selective tree cache invalidation after invoke."""
from __future__ import annotations

from unittest import mock

from tools.ui_automation import _maybe_invalidate_tree_after_act


def test_clear_history_invalidates():
    with mock.patch("detection.orchestrator.invalidate_tree_cache") as inv:
        _maybe_invalidate_tree_after_act(
            {"success": True},
            "Calculadora",
            acted_automation_id="ClearHistory",
        )
    inv.assert_called_once_with("Calculadora")


def test_num_button_does_not_invalidate():
    with mock.patch("detection.orchestrator.invalidate_tree_cache") as inv:
        _maybe_invalidate_tree_after_act(
            {"success": True},
            "Calculadora",
            acted_automation_id="num2Button",
        )
    inv.assert_not_called()

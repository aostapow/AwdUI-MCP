"""Spy invoke falls back to SelectionItemPattern for UWP NavView items."""
from __future__ import annotations

from unittest.mock import patch

from tools.spy_bridge import spy_invoke_element


def test_spy_invoke_returns_toggle_pattern():
    with patch("tools.spy_bridge._call") as mock_call:
        mock_call.return_value = {"success": True, "method": "TogglePattern"}
        result = spy_invoke_element(automation_id="trigButton", window_title="Calculadora")
    assert result["success"] is True
    assert result["method"] == "TogglePattern"


def test_spy_invoke_returns_selection_item_pattern():
    with patch("tools.spy_bridge._call") as mock_call:
        mock_call.return_value = {"success": True, "method": "SelectionItemPattern"}
        result = spy_invoke_element(name="Standard", window_title="Calculadora")
    assert result["success"] is True
    assert result["method"] == "SelectionItemPattern"
    mock_call.assert_called_once_with(
        "invoke",
        {"name": "Standard", "automation_id": "", "window_title": "Calculadora"},
    )


def test_build_critical_questions_flags_incomplete():
    from importlib.util import module_from_spec, spec_from_file_location
    from pathlib import Path

    hook_path = Path(__file__).resolve().parents[1] / ".cursor" / "hooks" / "check_mcp_objective.py"
    spec = spec_from_file_location("check_mcp_objective", hook_path)
    mod = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)

    state = {
        "objective_met": False,
        "current_focus": "uwp_nav_listitem",
        "blockers": ["NavView ListItem"],
        "criteria_status": [{"criterion": "invoke num1", "status": "not_met"}],
        "tasks": [{"id": "uwp_nav_listitem", "status": "pending"}],
        "last_cycle": {"live_verify": "invoke_element no probado"},
    }
    qs = mod.build_critical_questions(state)
    assert any("objective_met" in q for q in qs)
    assert any("blockers" in q for q in qs)
    assert any("criterio" in q for q in qs)

"""Tests for learning-cycle fix_in_cycle gate."""
from __future__ import annotations

import json
from pathlib import Path

from fix_in_cycle_gate import (
    audit_learning_turn,
    build_fix_gate_followup,
    flow_has_open_actionable_friction,
    is_actionable_friction,
)


def test_skill_only_friction_not_actionable():
    entry = {
        "type": "friction",
        "component": "repo_hints_set",
        "fix_in_cycle": "not_attempted",
    }
    assert is_actionable_friction(entry) is False


def test_structural_friction_actionable():
    entry = {
        "type": "friction",
        "component": "find_element",
        "fix_in_cycle": "not_attempted",
    }
    assert is_actionable_friction(entry) is True


def test_resolved_by_fix_applied_line(tmp_path: Path):
    flow_id = "F-06"
    lines = [
        {
            "ts": "2026-09-10T10:00:00Z",
            "type": "friction",
            "flow_id": flow_id,
            "component": "invoke_element",
            "fix_in_cycle": "not_attempted",
        },
        {
            "ts": "2026-09-10T10:05:00Z",
            "kind": "fix_applied",
            "flow_id": flow_id,
            "outcome": "ok",
        },
    ]
    assert flow_has_open_actionable_friction(lines, flow_id) is None


def test_audit_blocks_open_friction_on_active_lab(tmp_path: Path):
    imp = tmp_path / "improvements.jsonl"
    imp.write_text(
        json.dumps(
            {
                "type": "friction",
                "flow_id": "F-153",
                "component": "expand_element",
                "symptom": "slow",
                "fix_in_cycle": "not_attempted",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    state = {
        "active_lab": "Escritorio de Windows",
        "active_run": "test-run",
        "last_cycle": {
            "mode": "lab_execute",
            "flow_id": "F-153",
        },
    }
    result = audit_learning_turn(state, improvements_path=imp)
    assert result.blocked is True
    msg = build_fix_gate_followup(result)
    assert "FIX_IN_CYCLE BLOQUEADO" in msg


def test_audit_clear_without_active_lab(tmp_path: Path):
    imp = tmp_path / "improvements.jsonl"
    imp.write_text(
        json.dumps(
            {
                "type": "friction",
                "flow_id": "F-1",
                "component": "find_element",
                "fix_in_cycle": "not_attempted",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    state = {"active_lab": None, "last_cycle": {"flow_id": "F-1"}}
    result = audit_learning_turn(state, improvements_path=imp)
    assert result.blocked is False


def test_friction_logged_requires_fix_gate(tmp_path: Path):
    state = {
        "active_lab": "Calc",
        "active_run": "r",
        "last_cycle": {
            "mode": "lab_execute",
            "flow_id": "F-01",
            "friction_logged": True,
            "fix_gate": {"status": "pending"},
        },
    }
    result = audit_learning_turn(state, improvements_path=tmp_path / "missing.jsonl")
    assert result.blocked is True
    assert result.reason == "fix_gate_incomplete"

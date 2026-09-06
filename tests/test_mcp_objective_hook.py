"""Tests for MCP objective hook helper."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".cursor" / "hooks" / "check_mcp_objective.py"
STATE = ROOT / ".cursor" / "mcp-improvement-cycle" / "state.json"


def _run(mode: str) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(HOOK), "--mode", mode],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout.strip()


def test_status_incomplete_when_objective_not_met():
    if not STATE.is_file():
        return
    state = json.loads(STATE.read_text(encoding="utf-8"))
    if state.get("objective_met"):
        return
    paused = ROOT / ".cursor" / "mcp-improvement-cycle" / "PAUSED"
    had_paused = paused.is_file()
    saved_state = STATE.read_text(encoding="utf-8") if STATE.is_file() else ""
    try:
        if paused.is_file():
            paused.unlink()
        if STATE.is_file():
            data = json.loads(STATE.read_text(encoding="utf-8"))
            ctrl = data.get("cycle_control") or {}
            ctrl["paused"] = False
            data["cycle_control"] = ctrl
            data["status"] = "running"
            data["objective_met"] = False
            data["calculator_perfect"] = False
            STATE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        code, out = _run("status")
        if code == 0 and "cycle_paused" in out:
            pytest.skip("cycle paused in environment")
        assert code == 1
        assert "objective_met: false" in out
    finally:
        if had_paused:
            paused.parent.mkdir(parents=True, exist_ok=True)
            paused.write_text("paused\n", encoding="utf-8")
        if saved_state:
            STATE.write_text(saved_state, encoding="utf-8")


def test_stop_emits_empty_when_paused(tmp_path):
    paused = ROOT / ".cursor" / "mcp-improvement-cycle" / "PAUSED"
    had_paused = paused.is_file()
    try:
        paused.parent.mkdir(parents=True, exist_ok=True)
        paused.write_text("paused\n", encoding="utf-8")
        code, out = _run("stop")
        assert code == 0
        data = json.loads(out) if out else {}
        assert "followup_message" not in data
    finally:
        if had_paused:
            paused.write_text("paused\n", encoding="utf-8")
        elif paused.is_file():
            paused.unlink()


def test_stop_emits_followup_when_incomplete():
    if not STATE.is_file():
        return
    state = json.loads(STATE.read_text(encoding="utf-8"))
    if state.get("objective_met"):
        return
    paused = ROOT / ".cursor" / "mcp-improvement-cycle" / "PAUSED"
    had_paused = paused.is_file()
    saved_state = STATE.read_text(encoding="utf-8") if STATE.is_file() else ""
    try:
        if paused.is_file():
            paused.unlink()
        if STATE.is_file():
            data = json.loads(STATE.read_text(encoding="utf-8"))
            ctrl = data.get("cycle_control") or {}
            ctrl["paused"] = False
            data["cycle_control"] = ctrl
            data["status"] = "running"
            data["objective_met"] = False
            data["calculator_perfect"] = False
            STATE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        code, out = _run("stop")
        if not out:
            pytest.skip("hook emitted empty output (cycle paused or complete)")
        assert code == 0
        data = json.loads(out)
        assert "followup_message" in data
        assert "OBJETIVO MCP INCOMPLETO" in data["followup_message"]
    finally:
        if had_paused:
            paused.parent.mkdir(parents=True, exist_ok=True)
            paused.write_text("paused\n", encoding="utf-8")
        if saved_state:
            STATE.write_text(saved_state, encoding="utf-8")

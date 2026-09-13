"""Tests for MCP objective hook (auto-continue loop)."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".cursor" / "hooks" / "check_mcp_objective.py"


def _load_hook():
    spec = importlib.util.spec_from_file_location("check_mcp_objective", HOOK)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(HOOK.parent))
    spec.loader.exec_module(mod)
    return mod


def test_is_complete_only_objective_met():
    mod = _load_hook()
    assert mod.is_complete({"objective_met": False}) is False
    assert mod.is_complete({"objective_met": True}) is True
    assert (
        mod.is_complete(
            {
                "objective_met": True,
                "notepad_perfect": False,
                "teams_perfect": False,
            }
        )
        is True
    )


def test_stop_message_mcp_focus_without_active_lab():
    mod = _load_hook()
    msg = mod.build_continue_message(
        {
            "objective_met": False,
            "active_lab": None,
            "current_focus": "find_element perf",
            "blockers": [],
            "criteria_status": [{"criterion": "Eficiencia", "status": "partial"}],
            "last_cycle": {"live_verify": "ok"},
        }
    )
    assert "OBJETIVO MCP INCOMPLETO" in msg
    assert "active_lab=null" in msg
    assert "TE-07" not in msg
    assert "teams_perfect" not in msg
    assert "awdui-mcp-automejora" in msg


def test_eligible_execute_respects_parent_met():
    mod = _load_hook()
    flows = [
        {"id": "F-01", "kind": "entry", "status": "pending", "priority": 1},
        {
            "id": "F-02",
            "kind": "action",
            "status": "pending",
            "priority": 1,
            "parent_id": "F-01",
        },
    ]
    eligible = mod._eligible_execute_flows(flows)
    ids = {f["id"] for f in eligible}
    assert "F-01" in ids
    assert "F-02" not in ids
    flows[0]["status"] = "met"
    eligible = mod._eligible_execute_flows(flows)
    ids = {f["id"] for f in eligible}
    assert "F-02" in ids


def test_lab_flow_hint_execute_after_discover():
    mod = _load_hook()
    import tempfile
    import shutil

    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp) / "runs" / "test-run"
        run_dir.mkdir(parents=True)
        flows = {
            "flows": [
                {
                    "id": "F-01",
                    "title": "Suma 2+2",
                    "kind": "action",
                    "status": "pending",
                    "priority": 1,
                }
            ],
            "cycle": {"last_mode": "discover_flows"},
        }
        (run_dir / "flows.json").write_text(
            __import__("json").dumps(flows), encoding="utf-8"
        )
        # Patch _run_dir by passing state that hook resolves — use monkeypatch on module
        orig = mod._run_dir

        def fake_run_dir(state):
            return run_dir

        mod._run_dir = fake_run_dir
        hint = mod._lab_flow_hint({"active_run": "test-run"})
        mod._run_dir = orig
        assert "execute_flow F-01" in hint


def test_lab_flow_hint_discover_after_execute():
    mod = _load_hook()
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp) / "runs" / "test-run"
        run_dir.mkdir(parents=True)
        flows = {
            "flows": [
                {
                    "id": "F-01",
                    "kind": "entry",
                    "title": "Menu",
                    "status": "met",
                    "subtree_discovered": False,
                    "priority": 1,
                }
            ],
            "cycle": {"last_mode": "execute_flow"},
        }
        (run_dir / "flows.json").write_text(
            __import__("json").dumps(flows), encoding="utf-8"
        )
        orig = mod._run_dir
        mod._run_dir = lambda state: run_dir
        hint = mod._lab_flow_hint({"active_run": "test-run"})
        mod._run_dir = orig
        assert "discover_flows" in hint
        assert "subarbol" in hint


def test_stop_message_with_active_lab():
    mod = _load_hook()
    msg = mod.build_continue_message(
        {
            "objective_met": False,
            "active_lab": "teams",
            "active_run": "teams-2026-09-07",
            "current_focus": "discovery",
            "blockers": [],
            "criteria_status": [],
            "lab_apps": {
                "teams": {"perfect": False, "matrix_progress": {"met": 5, "total": 10}},
            },
            "last_cycle": {"live_verify": "ok"},
        }
    )
    assert "active_lab=teams" in msg
    assert "Lab activo 'teams'" in msg
    assert "autodetect" in msg or "discovered.yaml" in msg or "flows.json" in msg


def test_critical_questions_lab_includes_narration_check():
    mod = _load_hook()
    questions = mod.build_critical_questions(
        {
            "objective_met": False,
            "active_lab": "Demo",
            "active_run": "demo-run",
            "lab_apps": {"Demo": {"perfect": False}},
            "blockers": [],
            "last_cycle": {"live_verify": "ok", "mode": "execute_flow", "observed": "ok"},
        }
    )
    assert any("narrada" in q.lower() for q in questions)


def test_continue_message_dict_blockers():
    mod = _load_hook()
    msg = mod.build_continue_message(
        {
            "objective_met": False,
            "active_lab": "Calculadora",
            "current_focus": "lab",
            "blockers": [{"app": "Teams", "text": "slow list_elements"}],
            "criteria_status": [],
            "lab_apps": {"Calculadora": {}},
            "last_cycle": {},
        }
    )
    assert "Teams: slow list_elements" in msg


def test_continue_message_includes_narration_hint():
    mod = _load_hook()
    msg = mod.build_continue_message(
        {
            "objective_met": False,
            "active_lab": "teams",
            "active_run": "teams-run",
            "current_focus": "lab",
            "blockers": [],
            "criteria_status": [],
            "lab_apps": {"teams": {"perfect": False}},
            "last_cycle": {"live_verify": "ok"},
        }
    )
    assert "Narrar" in msg or "action-narration" in msg


def test_session_bootstrap_includes_narration_hint():
    mod = _load_hook()
    state_path = ROOT / ".cursor" / "mcp-improvement-cycle" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8-sig"))
    msg = mod.build_session_bootstrap(state)
    assert "NARRAR" in msg or "Voy a" in msg


def test_stop_hook_json_shape():
    mod = _load_hook()
    state_path = ROOT / ".cursor" / "mcp-improvement-cycle" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8-sig"))
    assert mod.is_complete(state) is False
    msg = mod.build_continue_message(state)
    payload = {"followup_message": msg}
    assert "followup_message" in payload

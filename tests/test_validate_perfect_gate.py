"""Tests for lab perfect gate validation."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_perfect_gate import (  # noqa: E402
    apply_perfect_flag,
    evaluate_perfect_gate,
)


def _minimal_run(tmp_path: Path, *, with_evidence: bool = True) -> Path:
    run = tmp_path / "demo-run"
    run.mkdir()
    (run / "discovered.yaml").write_text("app_name: Demo\nframework: uwp\n", encoding="utf-8")
    (run / "flows.json").write_text(
        json.dumps(
            {
                "flows": [
                    {
                        "id": "F-01",
                        "kind": "entry",
                        "source": "seed",
                        "status": "met",
                        "subtree_discovered": True,
                        "notes": "",
                    }
                ],
                "cycle": {"last_mode": "execute_flow"},
            }
        ),
        encoding="utf-8",
    )
    (run / "mcp-usage.jsonl").write_text(
        json.dumps({"tool": "find_element", "outcome": "ok", "timing_ms": 400}) + "\n",
        encoding="utf-8",
    )
    (run / "coverage.json").write_text(
        json.dumps({"generated_at": "2026-01-01T00:00:00Z", "usage": {}}),
        encoding="utf-8",
    )
    if with_evidence:
        (run / "evidence.jsonl").write_text(
            json.dumps(
                {
                    "flow_id": "F-01",
                    "mode": "execute_flow",
                    "phase": "verify",
                    "timing_ms": 200,
                }
            )
            + "\n",
            encoding="utf-8",
        )
    (run / "repo-snapshot.json").write_text(
        json.dumps({"app_name": "Demo", "object_count": 0, "objects": []}),
        encoding="utf-8",
    )
    return run


def test_gate_eligible_minimal(tmp_path):
    run = _minimal_run(tmp_path)
    result = evaluate_perfect_gate(run, app_name="Demo", state={"blockers": []})
    assert result["eligible"] is True
    assert result["blockers"] == []


def test_gate_blocks_missing_evidence(tmp_path):
    run = _minimal_run(tmp_path, with_evidence=False)
    result = evaluate_perfect_gate(run, app_name="Demo", state={"blockers": []})
    assert result["eligible"] is False
    assert any("G4_evidence" in b for b in result["blockers"])


def test_gate_blocks_pending_seed(tmp_path):
    run = _minimal_run(tmp_path)
    flows = json.loads((run / "flows.json").read_text(encoding="utf-8"))
    flows["flows"][0]["status"] = "pending"
    (run / "flows.json").write_text(json.dumps(flows), encoding="utf-8")
    result = evaluate_perfect_gate(run, app_name="Demo", state={"blockers": []})
    assert result["eligible"] is False
    assert any("G1_seeds" in b for b in result["blockers"])


def test_gate_blocks_missing_repo_snapshot(tmp_path):
    run = _minimal_run(tmp_path)
    (run / "repo-snapshot.json").unlink()
    result = evaluate_perfect_gate(run, app_name="Demo", state={"blockers": []})
    assert result["eligible"] is False
    assert any("G8_repo_snapshot" in b for b in result["blockers"])


def test_gate_blocks_slow_outcome(tmp_path):
    run = _minimal_run(tmp_path)
    (run / "mcp-usage.jsonl").write_text(
        json.dumps({"tool": "list_elements", "outcome": "slow", "timing_ms": 12000})
        + "\n",
        encoding="utf-8",
    )
    result = evaluate_perfect_gate(run, app_name="Demo", state={"blockers": []})
    assert result["eligible"] is False
    assert any("G6_latency" in b for b in result["blockers"])


def test_gate_blocks_global_blockers(tmp_path):
    run = _minimal_run(tmp_path)
    result = evaluate_perfect_gate(
        run,
        app_name="Demo",
        state={"blockers": [{"id": "b1", "message": "find slow"}]},
    )
    assert result["eligible"] is False
    assert any("G7_blockers" in b for b in result["blockers"])


def test_apply_perfect_flag(tmp_path):
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"lab_apps": {"Demo": {}}}), encoding="utf-8")
    assert apply_perfect_flag(state_path, "Demo", True) is True
    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert data["lab_apps"]["Demo"]["perfect"] is True
    assert apply_perfect_flag(state_path, "Demo", False) is False

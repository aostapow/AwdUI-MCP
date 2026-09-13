"""Detection baseline manifest aggregation."""
from __future__ import annotations

import json
from pathlib import Path

from detection_baseline_lib import (
    baseline_cell_key,
    baseline_hint_for_fix,
    cell_is_efficient,
    finalize_cell,
    ingest_usage_row,
    merge_runs,
)


def test_ingest_and_finalize_percentiles():
    acc: dict = {}
    rows = [
        {"tool": "find_element", "timing_ms": 100, "outcome": "ok", "framework": "uwp"},
        {"tool": "find_element", "timing_ms": 200, "outcome": "ok", "framework": "uwp"},
        {"tool": "find_element", "timing_ms": 300, "outcome": "ok", "framework": "uwp"},
        {"tool": "find_element", "timing_ms": 400, "outcome": "ok", "framework": "uwp"},
    ]
    for r in rows:
        ingest_usage_row(acc, r, run_id="run-a", default_framework="unknown")
    key = baseline_cell_key("uwp", "find_element", "*")
    cell = finalize_cell(acc[key])
    assert cell["samples"] == 4
    assert cell["p50_ms"] == 250
    assert cell["p95_ms"] >= 350


def test_merge_runs_from_tmp(tmp_path: Path):
    run = tmp_path / "calc-run"
    run.mkdir()
    (run / "discovered.yaml").write_text("framework: uwp\n", encoding="utf-8")
    lines = [
        {
            "ts": "2026-09-01T00:00:00Z",
            "tool": "invoke_element",
            "timing_ms": 450,
            "outcome": "ok",
            "uia_role": "Button",
        },
    ]
    (run / "mcp-usage.jsonl").write_text(
        json.dumps(lines[0]) + "\n",
        encoding="utf-8",
    )
    data = merge_runs([run])
    assert "calc-run" in data["source_runs"]
    cells = data["cells"]
    assert any(c["tool"] == "invoke_element" for c in cells.values())


def test_baseline_hint_prefers_framework_when_efficient():
    baseline = {
        "slow_threshold_ms": 3000,
        "cells": {
            baseline_cell_key("uwp", "find_element", "*"): {
                "framework": "uwp",
                "tool": "find_element",
                "uia_role": "*",
                "samples": 10,
                "p50_ms": 200,
                "p95_ms": 500,
                "ok_count": 10,
                "slow_count": 0,
                "fail_count": 0,
            }
        },
    }
    hint = baseline_hint_for_fix(
        baseline,
        framework="uwp",
        tool="find_element",
        abstraction="generic",
    )
    assert "preferir abstraction=framework" in hint
    assert cell_is_efficient(baseline["cells"][baseline_cell_key("uwp", "find_element", "*")])

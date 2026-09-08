"""Tests for lab coverage catalog and reporting."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lab_coverage_lib import (  # noqa: E402
    aggregate_usage,
    build_capability_catalog,
    build_lab_report,
    format_markdown_report,
    load_jsonl,
    write_lab_report,
)


def test_build_capability_catalog_has_tools_and_controls():
    cat = build_capability_catalog()
    assert cat["mcp_tools"]["total"] >= 50
    assert cat["uia_controls"]["total"] >= 20
    assert cat["act_bindings"]["total"] > 0


def test_aggregate_usage_coverage_pct():
    catalog = {
        "mcp_tools": {"tools": {"a": {}, "b": {}, "c": {}, "d": {}}},
        "uia_controls": {"controls": {"Button": {}, "Edit": {}, "MenuItem": {}}},
        "uia_patterns_ms": ["Invoke", "Value"],
        "act_methods": {"ids": ["map_invoke", "map_value"]},
        "act_bindings": {
            "items": [
                {"control": "Button", "act_method": "map_invoke", "tool": "invoke_element"},
            ]
        },
    }
    usage = [
        {
            "tool": "invoke_element",
            "uia_role": "Button",
            "uia_pattern": "Invoke",
            "act_method": "map_invoke",
            "uia_control": "Button",
            "interacted": True,
            "outcome": "ok",
        },
        {"tool": "list_elements", "uia_role": "Edit", "interacted": False},
    ]
    agg = aggregate_usage(catalog, usage, framework="uwp")
    assert agg["mcp_tools"]["used_total"] == 2
    assert agg["mcp_tools"]["universe_total"] == 4
    assert agg["mcp_tools"]["coverage_pct"] == 50.0
    assert "Button" in agg["uia_controls"]["interacted"]
    assert "Edit" in agg["uia_controls"]["seen_not_interacted"]


def test_write_lab_report(tmp_path):
    run = tmp_path / "demo-run"
    run.mkdir()
    (run / "discovered.yaml").write_text(
        "app_name: Demo\nframework: uwp\n", encoding="utf-8"
    )
    (run / "mcp-usage.jsonl").write_text(
        json.dumps({"tool": "find_element", "outcome": "ok", "timing_ms": 100}) + "\n",
        encoding="utf-8",
    )
    (run / "improvements.jsonl").write_text(
        json.dumps(
            {
                "kind": "mcp_code",
                "summary": "fix X",
                "benefit": "faster",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run / "flows.json").write_text(
        json.dumps({"flows": [{"id": "F-01", "status": "met", "kind": "entry", "source": "seed"}]}),
        encoding="utf-8",
    )
    catalog = {
        "generated_at": "2026-01-01T00:00:00Z",
        "mcp_tools": {"total": 2, "tools": {"find_element": {}, "click_element": {}}},
        "uia_controls": {"total": 1, "controls": {"Button": {}}},
        "uia_patterns_ms": ["Invoke"],
        "act_methods": {"ids": []},
        "act_bindings": {"items": []},
    }
    cat_path = tmp_path / "catalog.json"
    cat_path.write_text(json.dumps(catalog), encoding="utf-8")

    json_path, md_path = write_lab_report(run, cat_path)
    assert json_path.is_file()
    assert md_path.is_file()
    report = json.loads(json_path.read_text(encoding="utf-8"))
    assert report["usage"]["mcp_tools"]["used_total"] == 1
    md = format_markdown_report(report)
    assert "Cobertura MCP" in md
    assert "Mejoras MCP" in md


def test_incremental_sync_state_coverage(tmp_path):
    run = tmp_path / "demo-run"
    run.mkdir()
    (run / "discovered.yaml").write_text("app_name: Demo\nframework: uwp\n", encoding="utf-8")
    (run / "mcp-usage.jsonl").write_text(
        json.dumps({"tool": "find_element", "outcome": "ok"}) + "\n",
        encoding="utf-8",
    )
    (run / "flows.json").write_text(
        json.dumps(
            {
                "flows": [
                    {
                        "id": "F-01",
                        "kind": "entry",
                        "status": "met",
                        "subtree_discovered": True,
                        "source": "seed",
                    },
                    {
                        "id": "F-02",
                        "kind": "action",
                        "status": "pending",
                        "parent_id": "F-01",
                        "source": "discovered",
                    },
                ],
                "cycle": {"last_mode": "discover_flows"},
            }
        ),
        encoding="utf-8",
    )
    catalog = {
        "generated_at": "2026-01-01T00:00:00Z",
        "mcp_tools": {"total": 2, "tools": {"find_element": {}, "click_element": {}}},
        "uia_controls": {"total": 1, "controls": {"Button": {}}},
        "uia_patterns_ms": [],
        "act_methods": {"ids": []},
        "act_bindings": {"items": []},
    }
    cat_path = tmp_path / "catalog.json"
    cat_path.write_text(json.dumps(catalog), encoding="utf-8")
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps({"active_lab": "Demo", "active_run": "demo-run", "lab_apps": {}}),
        encoding="utf-8",
    )

    from lab_coverage_lib import incremental_lab_coverage

    result = incremental_lab_coverage(
        run,
        state_path=state_path,
        active_lab="Demo",
        active_run="demo-run",
        catalog_path=cat_path,
    )
    assert "tools 1/2" in result["summary_line"]
    state = json.loads(state_path.read_text(encoding="utf-8"))
    cov = state["lab_apps"]["Demo"]["coverage"]
    assert cov["mcp_tools_used"] == 1
    assert cov["mcp_tools_pct"] == 50.0
    assert (run / "coverage.json").is_file()
    fp = state["lab_apps"]["Demo"]["flows_progress"]
    assert fp["total"] == 2
    assert fp["met"] == 1
    assert fp["last_mode"] == "discover_flows"
    assert (run / "coverage-sync.json").is_file()


def test_coverage_diff_between_runs(tmp_path):
    runs = tmp_path / "runs"
    prev = runs / "app-2026-01-01"
    cur = runs / "app-2026-01-02"
    prev.mkdir(parents=True)
    cur.mkdir(parents=True)
    catalog = {
        "generated_at": "2026-01-01T00:00:00Z",
        "mcp_tools": {"total": 3, "tools": {"a": {}, "b": {}, "c": {}}},
        "uia_controls": {"total": 1, "controls": {"Button": {}}},
        "uia_patterns_ms": [],
        "act_methods": {"ids": []},
        "act_bindings": {"items": []},
    }
    cat_path = tmp_path / "catalog.json"
    cat_path.write_text(json.dumps(catalog), encoding="utf-8")

    (prev / "discovered.yaml").write_text("app_name: Demo\nframework: uwp\n", encoding="utf-8")
    (cur / "discovered.yaml").write_text("app_name: Demo\nframework: uwp\n", encoding="utf-8")
    (prev / "mcp-usage.jsonl").write_text(
        json.dumps({"tool": "find_element"}) + "\n", encoding="utf-8"
    )
    (cur / "mcp-usage.jsonl").write_text(
        json.dumps({"tool": "find_element"}) + "\n"
        + json.dumps({"tool": "click_element"}) + "\n",
        encoding="utf-8",
    )

    from lab_coverage_lib import build_coverage_diff, build_lab_report, write_coverage_diff

    write_lab_report(prev, cat_path)
    write_lab_report(cur, cat_path)
    out = write_coverage_diff(cur)
    assert out is not None
    diff = json.loads(out.read_text(encoding="utf-8"))
    assert "click_element" in diff["mcp_tools"]["newly_used"]


def test_load_jsonl_skips_bad_lines(tmp_path):
    p = tmp_path / "x.jsonl"
    p.write_text('{"a":1}\nnot json\n{"b":2}\n', encoding="utf-8")
    rows = load_jsonl(p)
    assert len(rows) == 2

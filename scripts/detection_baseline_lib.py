"""Aggregate detection timings from lab mcp-usage into a team manifest."""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = REPO_ROOT / ".cursor" / "mcp-improvement-cycle" / "runs"
DEFAULT_BASELINE_PATH = (
    REPO_ROOT / ".cursor" / "mcp-improvement-cycle" / "matrices" / "detection_baseline.json"
)
SLOW_THRESHOLD_MS = 3000

DETECTION_TOOLS = frozenset({
    "find_element",
    "find_all_elements",
    "list_elements",
    "invoke_element",
    "click_element",
    "expand_element",
    "expand_collapse_element",
    "get_snapshot",
    "spy_tree",
    "spy_inspect",
    "smart_find",
    "discover_control_interaction",
    "read_element",
    "read_element_by_index",
    "element_exists",
    "wait_for_element",
    "wait_for_condition",
    "ascii_ui_view",
    "detection_health",
    "get_focused_element",
    "list_control_items",
    "select_control_item",
})


def _percentile(sorted_vals: list[int], pct: float) -> Optional[int]:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * (pct / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    d0 = sorted_vals[f] * (c - k)
    d1 = sorted_vals[c] * (k - f)
    return int(round(d0 + d1))


def normalize_framework_label(raw: Optional[str]) -> str:
    try:
        from detection.frameworks.registry import normalize_framework_key

        return normalize_framework_key(raw)
    except Exception:
        key = (raw or "unknown").strip().lower()
        return "winui" if key == "winui" else (key or "unknown")


def baseline_cell_key(framework: str, tool: str, uia_role: str) -> str:
    fw = normalize_framework_label(framework)
    role = (uia_role or "*").strip() or "*"
    return f"{fw}|{tool}|{role}"


def _outcome_bucket(outcome: str) -> str:
    o = (outcome or "").lower()
    if o in ("ok", "fast", "met", "success"):
        return "ok"
    if "slow" in o or o in ("slow", "ok_warn", "warn"):
        return "slow"
    if o in ("fail", "not_found", "error", "partial"):
        return "fail"
    return "ok"


def ingest_usage_row(
    acc: dict[str, dict[str, Any]],
    row: dict[str, Any],
    *,
    run_id: str,
    default_framework: str,
) -> None:
    tool = str(row.get("tool") or row.get("mcp_tool") or "").strip()
    if not tool or tool not in DETECTION_TOOLS:
        return
    fw = normalize_framework_label(row.get("framework") or default_framework)
    role = str(row.get("uia_role") or row.get("role") or "*").strip() or "*"
    key = baseline_cell_key(fw, tool, role)
    cell = acc.setdefault(
        key,
        {
            "framework": fw,
            "tool": tool,
            "uia_role": role,
            "timings": [],
            "ok_count": 0,
            "slow_count": 0,
            "fail_count": 0,
            "last_ts": "",
            "run_ids": set(),
        },
    )
    cell["run_ids"].add(run_id)
    ts = str(row.get("ts") or "")
    if ts and ts >= cell.get("last_ts", ""):
        cell["last_ts"] = ts
    bucket = _outcome_bucket(str(row.get("outcome") or ""))
    if bucket == "ok":
        cell["ok_count"] += 1
    elif bucket == "slow":
        cell["slow_count"] += 1
    else:
        cell["fail_count"] += 1
    timing = row.get("timing_ms")
    if timing is None:
        return
    try:
        ms = int(timing)
    except (TypeError, ValueError):
        return
    if ms < 0:
        return
    cell["timings"].append(ms)


def finalize_cell(cell: dict[str, Any]) -> dict[str, Any]:
    timings = sorted(cell.pop("timings", []))
    run_ids = sorted(cell.pop("run_ids", set()))
    samples = len(timings)
    out = {
        "framework": cell["framework"],
        "tool": cell["tool"],
        "uia_role": cell["uia_role"],
        "samples": samples,
        "p50_ms": _percentile(timings, 50),
        "p95_ms": _percentile(timings, 95),
        "min_ms": timings[0] if timings else None,
        "max_ms": timings[-1] if timings else None,
        "ok_count": cell.get("ok_count", 0),
        "slow_count": cell.get("slow_count", 0),
        "fail_count": cell.get("fail_count", 0),
        "last_ts": cell.get("last_ts") or "",
        "run_ids": run_ids,
    }
    return out


def run_framework(run_dir: Path) -> str:
    discovered = run_dir / "discovered.yaml"
    if discovered.is_file():
        try:
            text = discovered.read_text(encoding="utf-8-sig")
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("framework:"):
                    return normalize_framework_label(line.split(":", 1)[1].strip().strip('"'))
        except OSError:
            pass
    cov = run_dir / "coverage.json"
    if cov.is_file():
        try:
            data = json.loads(cov.read_text(encoding="utf-8-sig"))
            return normalize_framework_label(data.get("framework"))
        except (json.JSONDecodeError, OSError):
            pass
    return "unknown"


def merge_runs(
    run_dirs: list[Path],
    *,
    usage_loader=None,
) -> dict[str, Any]:
    if usage_loader is None:
        from lab_coverage_lib import load_jsonl

        usage_loader = load_jsonl

    acc: dict[str, dict[str, Any]] = {}
    source_runs: list[str] = []
    for run_dir in sorted(run_dirs):
        usage_path = run_dir / "mcp-usage.jsonl"
        if not usage_path.is_file():
            continue
        run_id = run_dir.name
        source_runs.append(run_id)
        fw_default = run_framework(run_dir)
        for row in usage_loader(usage_path):
            ingest_usage_row(acc, row, run_id=run_id, default_framework=fw_default)

    cells = {k: finalize_cell(v) for k, v in sorted(acc.items())}
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "slow_threshold_ms": SLOW_THRESHOLD_MS,
        "source_runs": source_runs,
        "cells": cells,
    }


def discover_run_dirs(runs_root: Path | None = None) -> list[Path]:
    root = runs_root or RUNS_DIR
    if not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if p.is_dir() and (p / "mcp-usage.jsonl").is_file())


def write_baseline(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_baseline(path: Path | None = None) -> dict[str, Any]:
    p = path or DEFAULT_BASELINE_PATH
    if not p.is_file():
        return {"schema_version": 1, "cells": {}, "slow_threshold_ms": SLOW_THRESHOLD_MS}
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {"schema_version": 1, "cells": {}, "slow_threshold_ms": SLOW_THRESHOLD_MS}


def lookup_cell(
    baseline: dict[str, Any],
    framework: str,
    tool: str,
    uia_role: str = "*",
) -> Optional[dict[str, Any]]:
    cells = baseline.get("cells") or {}
    key = baseline_cell_key(framework, tool, uia_role)
    if key in cells:
        return cells[key]
    wildcard = baseline_cell_key(framework, tool, "*")
    return cells.get(wildcard)


def cell_is_efficient(cell: dict[str, Any], threshold_ms: int | None = None) -> bool:
    thr = threshold_ms or int(cell.get("slow_threshold_ms") or SLOW_THRESHOLD_MS)
    samples = int(cell.get("samples") or 0)
    p95 = cell.get("p95_ms")
    if samples < 3 or p95 is None:
        return False
    slow = int(cell.get("slow_count") or 0)
    ok = int(cell.get("ok_count") or 0)
    total_outcomes = slow + ok + int(cell.get("fail_count") or 0)
    if total_outcomes and slow / total_outcomes > 0.15:
        return False
    return int(p95) < thr


def baseline_hint_for_fix(
    baseline: dict[str, Any],
    *,
    framework: str,
    tool: str,
    uia_role: str = "*",
    abstraction: str = "",
) -> str:
    """Advisory text for fix_in_cycle (not a hard block)."""
    cell = lookup_cell(baseline, framework, tool, uia_role)
    if not cell:
        return ""
    thr = int(baseline.get("slow_threshold_ms") or SLOW_THRESHOLD_MS)
    fw, t, role = cell["framework"], cell["tool"], cell["uia_role"]
    samples = cell.get("samples", 0)
    p95 = cell.get("p95_ms")
    if abstraction == "generic" and cell_is_efficient(cell, thr):
        return (
            f"Baseline: {fw}/{t}/{role} ya eficiente (n={samples}, p95={p95}ms < {thr}ms) — "
            "preferir abstraction=framework o perfil en detection/frameworks/."
        )
    if p95 is not None and int(p95) >= thr and samples >= 2:
        return (
            f"Baseline: {fw}/{t}/{role} lento (p95={p95}ms, n={samples}) — fix_in_cycle justificado."
        )
    return ""

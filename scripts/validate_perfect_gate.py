#!/usr/bin/env python3
"""Validate lab_apps.{app}.perfect gate (G1–G7) from run artefacts."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
STATE_REL = REPO_ROOT / ".cursor/mcp-improvement-cycle/state.json"

SEED_SOURCES = frozenset({"seed", "user"})
DISCOVERY_TOOLS = frozenset(
    {"find_element", "list_elements", "smart_find", "find_elements", "find_elements_fuzzy"}
)
VERIFY_TOOLS = frozenset(
    {
        "read_element",
        "get_control_state",
        "element_exists",
        "wait_for_element",
        "get_element_properties",
        "get_snapshot",
    }
)

DEFAULT_THRESHOLDS: dict[str, Any] = {
    "discovery_p95_ms": 2000,
    "verify_p95_ms": 1500,
    "min_evidence_per_seed": 1,
    "min_invocations": 1,
}


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, int(0.95 * (len(ordered) - 1)))
    return float(ordered[idx])


def _check_record(check_id: str, ok: bool, detail: str) -> dict[str, Any]:
    return {"id": check_id, "ok": ok, "detail": detail}


def _seed_flows(flows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [f for f in flows if str(f.get("source") or "") in SEED_SOURCES]


def _flow_terminal_ok(flow: dict[str, Any]) -> bool:
    status = str(flow.get("status") or "")
    if status == "met":
        return True
    if status == "cancelled":
        return bool(str(flow.get("notes") or "").strip())
    return False


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _evidence_for_flow(evidence: list[dict[str, Any]], flow_id: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for row in evidence:
        fid = row.get("flow_id")
        if fid is None:
            continue
        if str(fid) == flow_id:
            hits.append(row)
    return hits


def _evidence_is_execute_step(row: dict[str, Any]) -> bool:
    mode = str(row.get("mode") or "")
    if mode == "execute_flow":
        return True
    if row.get("verify") or row.get("observed") or row.get("act"):
        return True
    phase = str(row.get("phase") or "").lower()
    return phase in {"obs", "act", "verify"}


def check_g1_seeds(flows: list[dict[str, Any]]) -> dict[str, Any]:
    seeds = _seed_flows(flows)
    if not seeds:
        return _check_record(
            "G1_seeds",
            False,
            "sin flujos seed/user — definir al menos uno o marcar perfect solo tras seeds",
        )
    bad = [f["id"] for f in seeds if not _flow_terminal_ok(f)]
    if bad:
        return _check_record(
            "G1_seeds",
            False,
            f"seeds pendientes o cancelled sin notes: {', '.join(bad)}",
        )
    return _check_record("G1_seeds", True, f"{len(seeds)} seed(s) met o cancelled con motivo")


def check_g2_autodetect(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "discovered.yaml"
    if not path.is_file():
        return _check_record("G2_autodetect", False, "falta discovered.yaml")
    if path.stat().st_size < 8:
        return _check_record("G2_autodetect", False, "discovered.yaml vacío")
    return _check_record("G2_autodetect", True, "discovered.yaml presente")


def check_g3_flows_valid(flows_data: dict[str, Any] | None) -> dict[str, Any]:
    if flows_data is None:
        return _check_record("G3_flows_valid", False, "falta flows.json")
    try:
        from validate_flows import validate_flows
    except ImportError:
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        from validate_flows import validate_flows  # type: ignore

    errors, warnings = validate_flows(flows_data)
    if errors:
        return _check_record(
            "G3_flows_valid",
            False,
            f"{len(errors)} error(es) estructurales — correr validate_flows.py",
        )
    suffix = f"; {len(warnings)} aviso(s) encolados" if warnings else ""
    return _check_record("G3_flows_valid", True, f"flows.json válido{suffix}")


def check_g4_evidence(
    flows: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    *,
    min_per_seed: int,
) -> dict[str, Any]:
    seeds_met = [
        f for f in _seed_flows(flows) if str(f.get("status") or "") == "met"
    ]
    if not seeds_met:
        return _check_record("G4_evidence", True, "sin seeds met — omitido")
    missing: list[str] = []
    for flow in seeds_met:
        fid = str(flow["id"])
        rows = [r for r in _evidence_for_flow(evidence, fid) if _evidence_is_execute_step(r)]
        if len(rows) < min_per_seed:
            missing.append(fid)
    if missing:
        return _check_record(
            "G4_evidence",
            False,
            f"sin evidence execute/verify para seeds met: {', '.join(missing)}",
        )
    return _check_record(
        "G4_evidence",
        True,
        f"evidence.jsonl cubre {len(seeds_met)} seed(s) met",
    )


def check_g5_coverage(run_dir: Path, state_entry: dict[str, Any] | None) -> dict[str, Any]:
    cov_path = run_dir / "coverage.json"
    state_cov = (state_entry or {}).get("coverage") or {}
    usage_rows = _load_jsonl(run_dir / "mcp-usage.jsonl")
    evidence_rows = _load_jsonl(run_dir / "evidence.jsonl")
    invocations = len(usage_rows) + len(evidence_rows)

    if not cov_path.is_file() and not state_cov.get("updated_at"):
        return _check_record(
            "G5_coverage",
            False,
            "falta coverage.json y lab_apps.*.coverage sin updated_at",
        )
    if invocations < DEFAULT_THRESHOLDS["min_invocations"]:
        return _check_record(
            "G5_coverage",
            False,
            "sin mcp-usage.jsonl ni evidence.jsonl — append uso MCP del lab",
        )
    return _check_record(
        "G5_coverage",
        True,
        f"cobertura registrada ({invocations} líneas usage/evidence)",
    )


def check_g6_latency(
    usage: list[dict[str, Any]],
    *,
    discovery_p95_ms: int,
    verify_p95_ms: int,
) -> dict[str, Any]:
    if not usage:
        return _check_record("G6_latency", True, "sin mcp-usage — omitido")

    slow_outcomes = [r for r in usage if str(r.get("outcome") or "").lower() == "slow"]
    if slow_outcomes:
        tools = sorted({str(r.get("tool") or "?") for r in slow_outcomes})
        return _check_record(
            "G6_latency",
            False,
            f"outcome slow en: {', '.join(tools)} ({len(slow_outcomes)} invocaciones)",
        )

    discovery_ms: list[float] = []
    verify_ms: list[float] = []
    for row in usage:
        tool = str(row.get("tool") or "")
        ms = row.get("timing_ms") or row.get("total_ms")
        if ms is None:
            continue
        try:
            val = float(ms)
        except (TypeError, ValueError):
            continue
        if tool in DISCOVERY_TOOLS:
            discovery_ms.append(val)
        elif tool in VERIFY_TOOLS:
            verify_ms.append(val)

    blockers: list[str] = []
    if discovery_ms:
        p95 = _p95(discovery_ms)
        if p95 > discovery_p95_ms:
            blockers.append(f"discovery p95 {p95:.0f}ms > {discovery_p95_ms}ms")
    if verify_ms:
        p95 = _p95(verify_ms)
        if p95 > verify_p95_ms:
            blockers.append(f"verify p95 {p95:.0f}ms > {verify_p95_ms}ms")

    if blockers:
        return _check_record("G6_latency", False, "; ".join(blockers))
    detail = "latencia dentro de umbrales"
    if discovery_ms or verify_ms:
        parts = []
        if discovery_ms:
            parts.append(f"discovery p95 {_p95(discovery_ms):.0f}ms")
        if verify_ms:
            parts.append(f"verify p95 {_p95(verify_ms):.0f}ms")
        detail = ", ".join(parts)
    return _check_record("G6_latency", True, detail)


def check_g7_blockers(state: dict[str, Any] | None, app_name: str | None) -> dict[str, Any]:
    blockers = (state or {}).get("blockers") or []
    if not blockers:
        return _check_record("G7_blockers", True, "sin blockers globales")

    relevant: list[Any] = []
    for item in blockers:
        if not isinstance(item, dict):
            relevant.append(item)
            continue
        lab = item.get("app") or item.get("lab")
        if not lab:
            relevant.append(item)
        elif app_name and app_name.lower() in str(lab).lower():
            relevant.append(item)
        elif not app_name:
            relevant.append(item)

    if relevant:
        return _check_record(
            "G7_blockers",
            False,
            f"{len(relevant)} blocker(s) activos en state.json",
        )
    return _check_record(
        "G7_blockers",
        True,
        "blockers solo de otras apps — no aplican",
    )


def check_g8_repo_snapshot(run_dir: Path) -> dict[str, Any]:
    if not (run_dir / "discovered.yaml").is_file():
        return _check_record("G8_repo_snapshot", True, "sin discovered.yaml — omitido")
    snap = run_dir / "repo-snapshot.json"
    if not snap.is_file():
        return _check_record(
            "G8_repo_snapshot",
            False,
            "falta repo-snapshot.json — correr hook incremental o repo_snapshot_lib",
        )
    return _check_record("G8_repo_snapshot", True, "repo-snapshot.json presente")


def evaluate_perfect_gate(
    run_dir: Path,
    *,
    state: dict[str, Any] | None = None,
    app_name: str | None = None,
    thresholds: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run G1–G7 checks. Returns eligible + checks + blockers list."""
    th = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    app = app_name or (state or {}).get("active_lab")
    state_entry = None
    if state and app:
        state_entry = (state.get("lab_apps") or {}).get(str(app)) or {}

    flows_path = run_dir / "flows.json"
    flows_data: dict[str, Any] | None = None
    flows: list[dict[str, Any]] = []
    if flows_path.is_file():
        try:
            flows_data = json.loads(flows_path.read_text(encoding="utf-8-sig"))
            flows = flows_data.get("flows") or []
        except (json.JSONDecodeError, OSError):
            flows_data = None

    evidence = _load_jsonl(run_dir / "evidence.jsonl")
    usage = _load_jsonl(run_dir / "mcp-usage.jsonl")

    checks = [
        check_g1_seeds(flows),
        check_g2_autodetect(run_dir),
        check_g3_flows_valid(flows_data),
        check_g4_evidence(
            flows,
            evidence,
            min_per_seed=int(th["min_evidence_per_seed"]),
        ),
        check_g5_coverage(run_dir, state_entry),
        check_g6_latency(
            usage,
            discovery_p95_ms=int(th["discovery_p95_ms"]),
            verify_p95_ms=int(th["verify_p95_ms"]),
        ),
        check_g7_blockers(state, str(app) if app else None),
        check_g8_repo_snapshot(run_dir),
    ]

    blockers = [f"{c['id']}: {c['detail']}" for c in checks if not c["ok"]]
    return {
        "eligible": len(blockers) == 0,
        "app": app,
        "run_dir": str(run_dir),
        "checks": {c["id"]: c for c in checks},
        "blockers": blockers,
        "evaluated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _resolve_run_dir(args: argparse.Namespace) -> tuple[Path, dict[str, Any] | None, str | None]:
    state: dict[str, Any] | None = None
    app_name: str | None = args.app
    if args.run_dir:
        return Path(args.run_dir), None, app_name
    if not STATE_REL.is_file():
        raise SystemExit(f"No state.json at {STATE_REL}")
    state = json.loads(STATE_REL.read_text(encoding="utf-8-sig"))
    active_run = state.get("active_run")
    if not active_run:
        raise SystemExit("active_run not set in state.json")
    app_name = app_name or state.get("active_lab")
    run_dir = REPO_ROOT / ".cursor/mcp-improvement-cycle/runs" / str(active_run)
    return run_dir, state, str(app_name) if app_name else None


def apply_perfect_flag(state_path: Path, app_name: str, eligible: bool) -> bool:
    """Set lab_apps.{app}.perfect only when eligible. Returns whether applied."""
    if not eligible or not state_path.is_file():
        return False
    data = json.loads(state_path.read_text(encoding="utf-8-sig"))
    lab_apps = data.setdefault("lab_apps", {})
    entry = lab_apps.setdefault(str(app_name), {})
    entry["perfect"] = True
    entry["perfect_gate"] = {
        "validated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "via": "validate_perfect_gate.py --apply",
    }
    state_path.write_text(json.dumps(data, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate lab perfect gate (G1–G7)")
    parser.add_argument("--run-dir", type=Path, help="Run directory (default: active_run)")
    parser.add_argument("--app", help="Lab app name (default: active_lab)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Set lab_apps.{app}.perfect=true in state.json if eligible",
    )
    parser.add_argument(
        "--skip-latency",
        action="store_true",
        help="Skip G6 latency check (not recommended for perfect)",
    )
    args = parser.parse_args()

    run_dir, state, app_name = _resolve_run_dir(args)
    if not run_dir.is_dir():
        print(f"Run dir not found: {run_dir}", file=sys.stderr)
        return 1

    thresholds = dict(DEFAULT_THRESHOLDS)
    if args.skip_latency:
        thresholds["discovery_p95_ms"] = 10**9
        thresholds["verify_p95_ms"] = 10**9

    result = evaluate_perfect_gate(
        run_dir,
        state=state,
        app_name=app_name,
        thresholds=thresholds,
    )

    if args.apply:
        if not app_name:
            print("--apply requires --app or active_lab in state.json", file=sys.stderr)
            return 1
        if apply_perfect_flag(STATE_REL, app_name, result["eligible"]):
            result["applied"] = True
        else:
            result["applied"] = False
            if not result["eligible"]:
                print("Not applied: gate not eligible", file=sys.stderr)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["eligible"]:
        print(f"OK — perfect gate eligible for {app_name or 'lab'} ({run_dir})")
    else:
        print(f"BLOCKED — perfect gate ({len(result['blockers'])} check(s)):", file=sys.stderr)
        for item in result["blockers"]:
            print(f"  - {item}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Learning-cycle gate: structural friction must not end a lab turn unresolved.

Outside active_lab, friction may stay in improvements.jsonl / _MCP_IMPROVEMENT for manual review.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

# Quirks documentable in skill/repo_hints only — no fix_in_cycle required.
SKILL_ONLY_COMPONENTS = frozenset({
    "repo_hints_set",
    "screenshot",
    "discover_flows",
    "lab_recovery",
    "discover_control_interaction",
    "press_key",
    "dismiss_flyout",
    "keyboard",
})

RESOLVED_FIX_IN_CYCLE = frozenset({
    "applied",
    "attempted",
    "not_needed",
    "n/a",
    "reverted",
    "legacy_debt",
})

FIX_OUTCOME_KINDS = frozenset({
    "fix_applied",
    "fix_reverted",
    "fix_attempt",
    "mcp_code",
})

LAB_MODES = frozenset({
    "lab_execute",
    "lab_discover",
    "fix_in_cycle",
})

# Shared detection core — generic fixes here need multi-framework regression evidence.
SHARED_CORE_PATH_MARKERS = (
    "detection/backends/uia_backend.py",
    "detection/uia_find.py",
    "detection/orchestrator.py",
    "detection/element_scope.py",
    "detection/uia_tree_cache.py",
)


@dataclass
class FixGateResult:
    blocked: bool
    reason: str = ""
    flow_id: str = ""
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "blocked": self.blocked,
            "reason": self.reason,
            "flow_id": self.flow_id,
            "detail": self.detail,
        }


def _entry_type(entry: dict) -> str:
    return str(entry.get("type") or entry.get("kind") or "").lower()


def _entry_flow_id(entry: dict) -> str:
    return str(entry.get("flow_id") or "").strip()


def _fix_in_cycle_value(entry: dict) -> str:
    return str(entry.get("fix_in_cycle") or "").strip().lower()


def is_skill_only_friction(entry: dict) -> bool:
    if _entry_type(entry) == "pattern":
        return True
    comp = str(entry.get("component") or "").strip()
    if comp in SKILL_ONLY_COMPONENTS:
        return True
    if entry.get("skill_only") is True:
        return True
    return False


def is_actionable_friction(entry: dict) -> bool:
    t = _entry_type(entry)
    if t not in ("friction", "gap"):
        return False
    if is_skill_only_friction(entry):
        return False
    fic = _fix_in_cycle_value(entry)
    if fic in RESOLVED_FIX_IN_CYCLE:
        return False
    if fic and fic != "not_attempted":
        return False
    return True


def load_improvements_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _fix_resolved_after(entries: list[dict], flow_id: str, after_ts: str) -> bool:
    """True if a fix line for flow_id exists at or after friction timestamp."""
    for e in entries:
        if _entry_flow_id(e) != flow_id:
            continue
        ts = str(e.get("ts") or "")
        if after_ts and ts and ts < after_ts:
            continue
        kind = _entry_type(e)
        if kind in ("fix_applied", "fix_reverted", "mcp_code"):
            return True
        if kind == "fix_attempt" and str(e.get("outcome") or "").lower() == "ok":
            return True
        fic = _fix_in_cycle_value(e)
        if fic in RESOLVED_FIX_IN_CYCLE and fic not in ("not_attempted", "attempted"):
            return True
    return False


def flow_has_open_actionable_friction(entries: list[dict], flow_id: str) -> Optional[dict]:
    """Latest actionable friction for flow_id that is still open."""
    if not flow_id:
        return None
    candidates = [
        e for e in entries
        if _entry_flow_id(e) == flow_id and is_actionable_friction(e)
    ]
    if not candidates:
        return None
    latest = candidates[-1]
    ts = str(latest.get("ts") or "")
    if _fix_resolved_after(entries, flow_id, ts):
        return None
    return latest


def _last_cycle_friction_logged(last_cycle: dict) -> bool:
    if last_cycle.get("friction_logged") is True:
        return True
    if last_cycle.get("structural_friction") is True:
        return True
    fg = last_cycle.get("fix_gate") or {}
    if fg.get("required") is True:
        return True
    return False


def _fix_gate_ok(last_cycle: dict) -> bool:
    fg = last_cycle.get("fix_gate") or {}
    status = str(fg.get("status") or "").lower()
    if status == "ok":
        return True
    outcome = str(fg.get("outcome") or "").lower()
    if outcome in ("fix_applied", "not_needed", "pending_manual", "waived_skill_only"):
        return True
    return False


def _touches_shared_core(files: Iterable[str]) -> bool:
    for raw in files:
        path = str(raw or "").replace("\\", "/").lower()
        if any(marker in path for marker in SHARED_CORE_PATH_MARKERS):
            return True
    return False


def audit_fix_regression_scope(state: dict) -> FixGateResult:
    """Lab: generic abstraction + shared core diff requires regression_frameworks (≥2)."""
    if not state.get("active_lab"):
        return FixGateResult(blocked=False, reason="no_active_lab")
    last = state.get("last_cycle") or {}
    fg = last.get("fix_gate") or {}
    abstraction = str(
        fg.get("abstraction") or last.get("fix_abstraction") or ""
    ).lower()
    if abstraction != "generic":
        return FixGateResult(blocked=False, reason="not_generic_abstraction")
    files = list(fg.get("files_touched") or last.get("files_touched") or [])
    if not files or not _touches_shared_core(files):
        return FixGateResult(blocked=False, reason="no_shared_core_touch")
    regression = list(fg.get("regression_frameworks") or last.get("regression_frameworks") or [])
    if len(regression) >= 2:
        return FixGateResult(blocked=False, reason="regression_matrix_ok")
    fw = str(fg.get("framework") or last.get("framework") or "?")
    return FixGateResult(
        blocked=True,
        reason="generic_fix_without_regression_matrix",
        flow_id=str(last.get("flow_id") or ""),
        detail=(
            f"fix abstraction=generic en núcleo compartido (framework turno={fw}) "
            "sin regression_frameworks (mín. 2 familias, ej. uwp + win32). "
            "Preferir abstraction=framework y detection/frameworks/<familia>/ "
            "o documentar re-VERIFY en improvements.jsonl."
        ),
    )


def audit_learning_turn(
    state: dict,
    improvements_path: Optional[Path] = None,
) -> FixGateResult:
    """Block lab turn close when structural friction was logged but fix_in_cycle did not run."""
    if not state.get("active_lab"):
        return FixGateResult(blocked=False, reason="no_active_lab")

    last = state.get("last_cycle") or {}
    mode = str(last.get("mode") or "").lower()
    if mode and mode not in LAB_MODES:
        return FixGateResult(blocked=False, reason="not_lab_mode")

    flow_id = str(last.get("flow_id") or "").strip()
    entries: list[dict] = []
    if improvements_path and improvements_path.is_file():
        entries = load_improvements_jsonl(improvements_path)
    elif state.get("active_run"):
        root = Path(__file__).resolve().parent.parent
        run_dir = root / ".cursor/mcp-improvement-cycle/runs" / str(state["active_run"])
        entries = load_improvements_jsonl(run_dir / "improvements.jsonl")

    open_entry = flow_has_open_actionable_friction(entries, flow_id) if flow_id else None
    turn_logged = _last_cycle_friction_logged(last)

    if open_entry is not None:
        ts = str(open_entry.get("ts") or "")
        if _fix_resolved_after(entries, flow_id, ts):
            return FixGateResult(blocked=False, reason="resolved_in_jsonl")
        comp = open_entry.get("component") or "?"
        symptom = (open_entry.get("symptom") or "")[:120]
        return FixGateResult(
            blocked=True,
            reason="unresolved_friction",
            flow_id=flow_id or _entry_flow_id(open_entry),
            detail=(
                f"fricción abierta ({comp}): {symptom}. "
                "Ejecutar fix_in_cycle (máx. 3 intentos) o cerrar con fix_in_cycle=not_needed "
                "solo si es skill-only; actualizar improvements.jsonl y last_cycle.fix_gate."
            ),
        )

    if turn_logged and not _fix_gate_ok(last):
        return FixGateResult(
            blocked=True,
            reason="fix_gate_incomplete",
            flow_id=flow_id,
            detail=(
                "last_cycle marca fricción estructural pero fix_gate.status no es 'ok' "
                "(outcome: fix_applied | not_needed | pending_manual | waived_skill_only)."
            ),
        )

    regression = audit_fix_regression_scope(state)
    if regression.blocked:
        return regression

    return FixGateResult(blocked=False, reason="clear")


def _baseline_advisory(state: dict) -> str:
    try:
        scripts = Path(__file__).resolve().parent
        import sys

        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        from detection_baseline_lib import baseline_hint_for_fix, load_baseline

        last = state.get("last_cycle") or {}
        fg = last.get("fix_gate") or {}
        fw = str(fg.get("framework") or last.get("framework") or "").strip()
        tool = str(
            fg.get("tool")
            or last.get("friction_tool")
            or (last.get("observe") or "").split()[0]
            or ""
        ).strip()
        if not fw or not tool:
            open_fr = last.get("friction_component")
            if open_fr:
                tool = str(open_fr)
        abstraction = str(fg.get("abstraction") or last.get("fix_abstraction") or "").lower()
        role = str(fg.get("uia_role") or last.get("uia_role") or "*")
        return baseline_hint_for_fix(
            load_baseline(),
            framework=fw or "unknown",
            tool=tool,
            uia_role=role,
            abstraction=abstraction,
        )
    except Exception:
        return ""


def build_fix_gate_followup(result: FixGateResult, state: dict | None = None) -> str:
    if not result.blocked:
        return ""
    fid = result.flow_id or "?"
    baseline_txt = ""
    if state:
        hint = _baseline_advisory(state)
        if hint:
            baseline_txt = f" {hint}"
    return (
        "FIX_IN_CYCLE BLOQUEADO (lab activo): no avanzar al siguiente flujo. "
        f"flow_id={fid}. {result.detail} "
        "Seguir .cursor/skills/awdui-mcp-automejora/references/patterns/fix-in-cycle.md: "
        "fix servidor → pytest → restart MCP → re-VERIFY mismo paso. "
        "Si 3 intentos fallan: revert + pending_manual_fixes. "
        "Fuera de lab las mejoras pueden quedar solo en _MCP_IMPROVEMENT/. "
        "Fixes genéricos en uia_backend/orchestrator: ver framework-profiles.md."
        f"{baseline_txt}"
    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Audit fix_in_cycle compliance for active lab.")
    parser.add_argument(
        "--state",
        default=".cursor/mcp-improvement-cycle/state.json",
        help="Path to state.json",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON result")
    args = parser.parse_args()

    path = Path(args.state)
    if not path.is_file():
        print("no state file")
        return 0
    state = json.loads(path.read_text(encoding="utf-8-sig"))
    result = audit_learning_turn(state)
    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False))
        return 1 if result.blocked else 0
    if result.blocked:
        print(build_fix_gate_followup(result, state))
        return 1
    print("fix_gate: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

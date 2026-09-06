#!/usr/bin/env python3
"""Read MCP improvement state and emit hook JSON or human status.

Used by Cursor hooks (stop / sessionStart) to keep the agent on mission.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

STATE_REL = Path(".cursor/mcp-improvement-cycle/state.json")
PAUSED_REL = Path(".cursor/mcp-improvement-cycle/PAUSED")
SKILL_REL = ".cursor/skills/awdui-mcp-objective/SKILL.md"


def _repo_root() -> Path:
    # Hook cwd is project root; fallback: script at .cursor/hooks/
    here = Path(__file__).resolve().parent
    return here.parent.parent if here.name == "hooks" else Path.cwd()


def load_state() -> dict | None:
    path = _repo_root() / STATE_REL
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def is_paused(state: dict | None = None) -> bool:
    """True when user paused the auto-continue loop (stop hook / sessionStart)."""
    root = _repo_root()
    if (root / PAUSED_REL).is_file():
        return True
    if state is None:
        state = load_state()
    if not state:
        return False
    ctrl = state.get("cycle_control") or {}
    if ctrl.get("paused") is True:
        return True
    if state.get("status") == "paused":
        return True
    return False


def is_complete(state: dict) -> bool:
    if state.get("objective_met") is True:
        return True
    if state.get("calculator_perfect") is True and state.get("mcp_infra_ready") is True:
        return True
    if state.get("status") == "complete" and state.get("calculator_perfect") is not False:
        return True
    return False


def _safe_text(text: str) -> str:
    return text.replace("\u2192", "->").replace("\u2014", "-")


def build_critical_questions(state: dict) -> list[str]:
    """Self-check before closing a turn — any 'no' means keep going."""
    questions: list[str] = []
    if state.get("objective_met") is True:
        questions.append("objective_met=true en state.json? SI")
        return questions

    questions.append("objective_met=true en state.json? NO -> continuar")
    for entry in state.get("criteria_status") or []:
        st = entry.get("status", "")
        if st != "met":
            short = (entry.get("criterion") or "")[:60]
            questions.append(f"criterio '{short}' cumplido con evidencia? NO ({st})")

    blockers = state.get("blockers") or []
    if blockers:
        questions.append(f"blockers resueltos? NO ({len(blockers)} activos)")

    last = state.get("last_cycle") or {}
    if not last.get("live_verify"):
        questions.append("ultimo ciclo verifico vivo con MCP? NO")
    elif "no probado" in str(last.get("live_verify", "")).lower():
        questions.append("ultima verificacion MCP completo el flujo ACTUAR? NO")

    focus = state.get("current_focus") or ""
    for task in state.get("tasks") or []:
        if task.get("id") == focus and task.get("status") not in ("done", "cancelled"):
            questions.append(f"task foco '{focus}' marcada done? NO ({task.get('status')})")
            break

    if state.get("calculator_perfect") is False:
        questions.append("calculator_perfect=true? NO -> continuar Calculadora (skill calculator-mcp-harness)")

    return questions


def build_session_bootstrap(state: dict) -> str:
    """Rich context injected at sessionStart so the agent runs without waiting."""
    last = state.get("last_cycle") or {}
    next_step = last.get("next") or state.get("current_focus") or "leer state.json"
    return _safe_text(
        "[MCP AUTO-CYCLE ACTIVE — ejecutar de inmediato, sin pedir permiso]\n"
        f"Leer primero: {SKILL_REL} y .cursor/skills/calculator-mcp-harness/SKILL.md y "
        f"{STATE_REL.as_posix()}.\n"
        f"objective_met=false, calculator_perfect=false. "
        f"Foco: {state.get('current_focus')}. Siguiente: {next_step}.\n"
        "Un ciclo ahora: launch_app(calc.exe) reuse o replace si stale → "
        "set_target_window(Calculadora) → OBSERVAR → ACTUAR → VERIFICAR "
        "(invoke_element con verify_* y citar timings) → screenshot hito → "
        "actualizar calculator_matrix y calculator_evidence.\n"
        "No esperar al usuario salvo que pregunte otra cosa explícita. "
        "Si el usuario solo saluda o pide continuar, arrancar el ciclo igual."
    )


def build_continue_message(state: dict) -> str:
    focus = state.get("current_focus") or "leer state.json"
    blockers = state.get("blockers") or []
    blocker_txt = "; ".join(_safe_text(b) for b in blockers) if blockers else "ninguno"
    criteria = state.get("completion_criteria") or []
    pending = []
    for entry in state.get("criteria_status") or []:
        if entry.get("status") != "met":
            pending.append(_safe_text(entry.get("criterion", "")[:80]))
    if not pending and criteria:
        pending = [_safe_text(c[:80]) for c in criteria]
    pending_txt = " | ".join(pending[:3]) if pending else "ver completion_criteria"
    checks = build_critical_questions(state)
    checks_txt = " ".join(checks[:5]) if checks else ""
    calc = state.get("calculator_perfect")
    calc_txt = "calculator_perfect=true" if calc is True else "calculator_perfect=false -> solo MCP agentico en Calculadora"
    return _safe_text(
        f"OBJETIVO MCP INCOMPLETO - continuar sin pedir permiso. "
        f"Leer {SKILL_REL} y .cursor/skills/calculator-mcp-harness/SKILL.md y {STATE_REL.as_posix()}. "
        f"{calc_txt}. Foco: {focus}. Blockers: {blocker_txt}. "
        f"Pendiente: {pending_txt}. "
        f"Auto-check: {checks_txt}. "
        f"Evaluar solo con tools MCP (sin scripts). Screenshot en hitos. "
        f"Un ciclo: observar -> actuar -> verificar -> actualizar calculator_matrix."
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("status", "stop", "session"),
        default="status",
        help="status=stdout human; stop=hook followup JSON; session=hook context JSON",
    )
    args = parser.parse_args()
    state = load_state()

    if state is None:
        if args.mode == "status":
            print("no state file")
            return 0
        return 0

    if is_paused(state):
        if args.mode == "status":
            print("objective_met: false")
            print("cycle_paused: true (stop hook will not inject followup)")
            ctrl = state.get("cycle_control") or {}
            reason = ctrl.get("paused_reason") or "PAUSED file or cycle_control.paused"
            print(f"reason: {reason}")
            print("Resume: scripts/resume-mcp-cycle.ps1")
            return 0
        # stop / session: emit nothing so Cursor does not auto-continue
        if args.mode == "stop":
            print(json.dumps({}, ensure_ascii=False))
        return 0

    if is_complete(state):
        if args.mode == "status":
            print("objective_met: true")
        return 0

    msg = build_continue_message(state)

    if args.mode == "status":
        print("objective_met: false")
        print(msg)
        return 1

    if args.mode == "stop":
        print(json.dumps({"followup_message": msg}, ensure_ascii=False))
        return 0

    if args.mode == "session":
        print(
            json.dumps(
                {"additional_context": build_session_bootstrap(state)},
                ensure_ascii=False,
            )
        )
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

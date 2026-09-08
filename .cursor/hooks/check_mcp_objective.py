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
SKILL_REL = ".cursor/skills/awdui-mcp-automejora/SKILL.md"
LAB_APPS_DIR = Path("lab-apps")


def _repo_root() -> Path:
    here = Path(__file__).resolve().parent
    return here.parent.parent if here.name == "hooks" else Path.cwd()


def _run_dir(state: dict) -> Path:
    root = _repo_root()
    active_run = state.get("active_run") or "run"
    return root / Path(".cursor/mcp-improvement-cycle/runs") / str(active_run)


def _discovered_path(state: dict) -> Path:
    return _run_dir(state) / "discovered.yaml"


def _override_path(active: str) -> Path | None:
    """Optional hints only when autodetect fails — lab-apps/overrides/{slug}.yaml."""
    root = _repo_root()
    slug = str(active).lower().replace(" ", "-")
    for rel in (
        root / LAB_APPS_DIR / "overrides" / f"{slug}.yaml",
        root / LAB_APPS_DIR / "overrides" / f"{active}.yaml",
    ):
        if rel.is_file():
            return rel
    return None


def load_state() -> dict | None:
    path = _repo_root() / STATE_REL
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
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


def _safe_text(text: str) -> str:
    return text.replace("\u2192", "->").replace("\u2014", "-")


def _lab_perfect(state: dict, lab_id: str) -> bool | None:
    """True/False if known; None if no data."""
    apps = state.get("lab_apps") or {}
    if lab_id in apps and "perfect" in apps[lab_id]:
        return apps[lab_id]["perfect"] is True
    legacy = f"{lab_id}_perfect"
    if legacy in state:
        return state[legacy] is True
    return None


def is_complete(state: dict) -> bool:
    """Cycle complete when objective_met is true."""
    return state.get("objective_met") is True


def _flows_path(state: dict) -> Path:
    return _run_dir(state) / "flows.json"


def _load_flows(state: dict) -> dict | None:
    path = _flows_path(state)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None


def _flows_by_id(flows: list) -> dict[str, dict]:
    return {str(f["id"]): f for f in flows if f.get("id")}


def _parent_met(flows: list, flow: dict) -> bool:
    parent_id = flow.get("parent_id")
    if not parent_id:
        return True
    parent = _flows_by_id(flows).get(str(parent_id))
    return parent is not None and parent.get("status") == "met"


def _eligible_execute_flows(flows: list) -> list[dict]:
    eligible = []
    for f in flows:
        if f.get("status") not in ("pending", "exploring", "partial"):
            continue
        if not _parent_met(flows, f):
            continue
        eligible.append(f)
    return eligible


def _entry_needs_subtree(flows: list) -> list[dict]:
    return [
        f
        for f in flows
        if f.get("kind") == "entry"
        and f.get("status") == "met"
        and f.get("subtree_discovered") is not True
    ]


def _sort_execute_candidates(flows: list[dict]) -> list[dict]:
    def sort_key(f: dict) -> tuple:
        kind_rank = 0 if f.get("kind") == "entry" else 1
        return (kind_rank, int(f.get("priority") or 99), str(f.get("id") or ""))

    return sorted(flows, key=sort_key)


def _discover_scope_hint(flows_data: dict) -> str:
    flows = flows_data.get("flows") or []
    cycle = flows_data.get("cycle") or {}
    scope = cycle.get("discover_scope") or {}
    parent_id = scope.get("parent_flow_id")
    if parent_id:
        return (
            f"subarbol de {parent_id} (solo action hijos coherentes; "
            "cerrar con subtree_discovered=true)"
        )
    needs = _entry_needs_subtree(flows)
    if needs:
        fid = needs[0].get("id", "?")
        return (
            f"priorizar subarbol de entry {fid} (reabrir menu si cerro); "
            "raiz solo entry nuevos"
        )
    return "raiz: nuevos menus/tabs/modos solo como kind:entry (sin hijos especulativos)"


def _lab_flow_hint(state: dict) -> str:
    """Next lab sub-mode: execute_flow vs discover_flows (alternating)."""
    flows_data = _load_flows(state)
    if flows_data is None:
        return (
            "crear runs/.../flows.json (seeds del usuario o vacio) -> "
            "discover_flows tras autodetect"
        )

    flows = flows_data.get("flows") or []
    cycle = flows_data.get("cycle") or {}
    last_mode = cycle.get("last_mode")
    eligible = _eligible_execute_flows(flows)
    total = len(flows)
    met = sum(1 for f in flows if f.get("status") == "met")

    if not flows:
        return "discover_flows obligatorio (catalogo vacio; escanear ventana raiz)"

    if last_mode == "execute_flow":
        scope = _discover_scope_hint(flows_data)
        return (
            f"discover_flows [{scope}]; encolar TODOS los candidatos del scan en flows.json "
            f"(no ejecutar aqui); catalogo {total} flujos ({met} met, {len(eligible)} ejecutables)"
        )

    if eligible:
        ordered = _sort_execute_candidates(eligible)
        nxt = ordered[0]
        fid = nxt.get("id", "?")
        kind = nxt.get("kind", "action")
        title = _safe_text(str(nxt.get("title") or "sin titulo")[:50])
        parent = nxt.get("parent_id")
        parent_txt = f" parent={parent}" if parent else ""
        return (
            f"execute_flow {fid} '{title}' kind={kind}{parent_txt} "
            f"(un paso OBS->ACT->VERIFY; catalogo {total} flujos)"
        )

    return (
        f"discover_flows [{_discover_scope_hint(flows_data)}]; "
        f"encolar todos los candidatos; sin ejecutables ({total} flujos, {met} met)"
    )


def _pending_criteria(state: dict) -> list[str]:
    pending = []
    for entry in state.get("criteria_status") or []:
        if entry.get("status") != "met":
            pending.append(_safe_text((entry.get("criterion") or "")[:80]))
    return pending


def _flows_validation_hint(state: dict) -> str:
    """Validate flows.json if present; return short hint for hook output."""
    flows_path = _run_dir(state) / "flows.json"
    if not flows_path.is_file():
        return ""
    try:
        scripts = _repo_root() / "scripts"
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        from validate_flows import validate_flows

        data = json.loads(flows_path.read_text(encoding="utf-8-sig"))
        errors, warnings = validate_flows(data)
        if errors:
            return f"flows.json INVALID ({len(errors)} errores) -> validate_flows.py"
        if warnings:
            return f"flows.json OK ({len(warnings)} avisos encolados)"
        return "flows.json OK"
    except Exception:
        return "flows.json: correr validate_flows.py"


def _perfect_gate_eval(state: dict) -> dict | None:
    """Run validate_perfect_gate if run dir exists."""
    active = state.get("active_lab")
    if not active:
        return None
    run_dir = _run_dir(state)
    if not run_dir.is_dir():
        return None
    try:
        scripts = _repo_root() / "scripts"
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        from validate_perfect_gate import evaluate_perfect_gate

        return evaluate_perfect_gate(
            run_dir,
            state=state,
            app_name=str(active),
        )
    except Exception:
        return None


def _perfect_gate_hint(state: dict) -> str:
    result = _perfect_gate_eval(state)
    if result is None:
        return ""
    if result.get("eligible"):
        return "perfect gate: elegible (validate_perfect_gate.py --apply)"
    n = len(result.get("blockers") or [])
    return f"perfect gate: bloqueado ({n} checks) -> validate_perfect_gate.py"


def _incremental_coverage(state: dict) -> str:
    """Regenerate coverage.json + lab-summary.md each lab turn (not only at end)."""
    active = state.get("active_lab")
    if not active:
        return ""
    run_dir = _run_dir(state)
    if not run_dir.is_dir():
        return ""
    scripts = _repo_root() / "scripts"
    try:
        import sys

        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        from lab_coverage_lib import incremental_lab_coverage

        result = incremental_lab_coverage(
            run_dir,
            state_path=_repo_root() / STATE_REL,
            active_lab=str(active),
            active_run=str(state.get("active_run") or run_dir.name),
        )
        flow_val = _flows_validation_hint(state)
        parts = [f"cobertura incremental: {result['summary_line']}"]
        if flow_val:
            parts.append(flow_val)
        gate_hint = _perfect_gate_hint(state)
        if gate_hint:
            parts.append(gate_hint)
        return "; ".join(parts)
    except Exception:
        return "cobertura: correr python scripts/lab_coverage_report.py"


def _lab_focus(state: dict) -> str:
    """Next work item — MCP-first unless active_lab is set."""
    active = state.get("active_lab")
    if active:
        run = state.get("active_run") or f"{active}-run"
        discovered = _discovered_path(state)
        discovered_txt = discovered.as_posix()
        perfect = _lab_perfect(state, str(active))
        status = "perfect" if perfect else "en curso"
        autodetect = (
            "autodetect: list_windows -> launch_app si falta -> detect_framework -> "
            "set_target_window -> escribir discovered.yaml; "
        )
        if discovered.is_file():
            autodetect = f"discovered.yaml listo ({discovered_txt}); "
        override = _override_path(str(active))
        hint = f" override {override.as_posix()}" if override else ""
        flow_hint = _lab_flow_hint(state)
        cov = _incremental_coverage(state)
        cov_txt = f" {cov}." if cov else ""
        return (
            f"Lab activo '{active}' ({status}): solo nombre de app — {autodetect}"
            f"{flow_hint}; append mcp-usage.jsonl + improvements.jsonl cada turno;{cov_txt} "
            f"runs/{run}/evidence.jsonl.{hint}"
        )

    pending = _pending_criteria(state)
    focus = state.get("current_focus") or "completion_criteria"
    if pending:
        return (
            f"Sin lab activo. Foco MCP: {focus}. "
            f"Criterios pendientes: {' | '.join(pending[:3])}."
        )
    last = state.get("last_cycle") or {}
    nxt = last.get("next") or focus
    return f"Sin lab activo. Foco MCP: {nxt}"


def build_critical_questions(state: dict) -> list[str]:
    """Self-check before closing a turn — any 'no' means keep going."""
    questions: list[str] = []
    last = state.get("last_cycle") or {}

    if state.get("objective_met") is True:
        questions.append("objective_met=true en state.json? SI")
        return questions

    questions.append("objective_met=true en state.json? NO -> continuar")

    for entry in state.get("criteria_status") or []:
        st = entry.get("status", "")
        if st != "met":
            short = (entry.get("criterion") or "")[:60]
            questions.append(f"criterio '{short}' cumplido con evidencia? NO ({st})")

    active = state.get("active_lab")
    if active:
        apps_entry = (state.get("lab_apps") or {}).get(str(active)) or {}
        perfect = _lab_perfect(state, str(active))
        if perfect is not True:
            prog = (apps_entry.get("matrix_progress") or {})
            met = prog.get("met", "?")
            total = prog.get("total", "?")
            questions.append(
                f"lab_apps.{active}.perfect=true? NO -> continuar corrida ({met}/{total})"
            )
        safety = apps_entry.get("safety") or {}
        if safety.get("message_allowlist"):
            questions.append(
                f"envio mensajes solo allowlist de {active}? verificar safety del turno"
            )
        safety_path = _run_dir(state) / "safety.yaml"
        if safety_path.is_file():
            try:
                text = safety_path.read_text(encoding="utf-8")
                if "message_allowlist" in text or "allowlist" in text:
                    questions.append(
                        f"envio mensajes solo allowlist de {active}? verificar runs safety.yaml"
                    )
            except OSError:
                pass
        cov = apps_entry.get("coverage") or {}
        if not cov.get("updated_at"):
            questions.append(
                "cobertura incremental actualizada (coverage.json)? NO -> append mcp-usage y regenerar"
            )
        flows_path = _run_dir(state) / "flows.json"
        if flows_path.is_file():
            hint = _flows_validation_hint(state)
            if "INVALID" in hint:
                questions.append(f"flows.json valido? NO ({hint})")
        gate = _perfect_gate_eval(state)
        if apps_entry.get("perfect") is True:
            if gate and not gate.get("eligible"):
                n = len(gate.get("blockers") or [])
                questions.append(
                    f"perfect=true pero gate G1-G8? NO ({n} checks) -> corregir o revertir flag"
                )
        elif gate and gate.get("eligible"):
            questions.append(
                "lab_apps perfect=false pero gate elegible? considerar --apply tras cierre honesto MCP"
            )
        if not last.get("mode") and not last.get("observed"):
            questions.append(
                "last_cycle actualizado (observed/act/verify)? NO -> cerrar turno lab"
            )
        questions.append(
            "cada accion GUI narrada en chat (Voy a...) ANTES de la tool? verificar turno"
        )
        questions.append(
            "friccion/workaround persistido en repo (repo_hints_set)? verificar si aplico"
        )
    elif last.get("live_verify") or "ast" in str(state.get("current_focus") or "").lower():
        questions.append(
            "cada accion GUI narrada en chat (Voy a...) ANTES de la tool? verificar turno"
        )
        questions.append(
            "friccion/workaround persistido en repo (repo_hints_set)? verificar si aplico"
        )

    blockers = state.get("blockers") or []
    if blockers:
        questions.append(f"blockers resueltos? NO ({len(blockers)} activos)")

    if not last.get("live_verify"):
        questions.append("ultimo ciclo verifico vivo con MCP? NO")
    elif "no probado" in str(last.get("live_verify", "")).lower():
        questions.append("ultima verificacion MCP completo el flujo ACTUAR? NO")

    focus = state.get("current_focus") or ""
    for task in state.get("tasks") or []:
        if task.get("id") == focus and task.get("status") not in ("done", "cancelled"):
            questions.append(f"task foco '{focus}' marcada done? NO ({task.get('status')})")
            break

    tvp = state.get("tool_validation_progress") or {}
    fail_n = int(tvp.get("fail") or 0)
    if fail_n > 0:
        questions.append(f"tool_validation fail=0? NO ({fail_n} fail)")

    return questions


def build_session_bootstrap(state: dict) -> str:
    """Rich context injected at sessionStart so the agent runs without waiting."""
    lab = _lab_focus(state)
    active = state.get("active_lab")
    lab_line = f" active_lab={active}." if active else " active_lab=null (sin evaluacion de app)."
    return _safe_text(
        "[MCP AUTO-CYCLE ACTIVE - ejecutar de inmediato, sin pedir permiso]\n"
        f"Leer primero: {SKILL_REL} y {STATE_REL.as_posix()}.\n"
        f"objective_met=false.{lab_line} "
        f"Foco: {state.get('current_focus')}. "
        f"Siguiente: {lab}\n"
        "Un ciclo ahora: NARRAR en chat (Voy a...; no es pedir permiso) -> "
        "OBSERVAR -> ACTUAR (una tool MCP por mensaje) -> "
        "VERIFICAR (timings + screenshot en hitos) -> append mcp-usage.jsonl -> "
        "cobertura incremental (coverage.json) -> actualizar state.json y "
        "runs/{active_run}/evidence.jsonl si lab activo.\n"
        "No esperar al usuario salvo pregunta explicita distinta. "
        "No declarar objective_met=true hasta completion_criteria y mcp_quality_status operational."
    )


def build_continue_message(state: dict) -> str:
    focus = state.get("current_focus") or "leer state.json"
    blockers = state.get("blockers") or []
    blocker_txt = "; ".join(_safe_text(b) for b in blockers) if blockers else "ninguno"
    pending = _pending_criteria(state)
    pending_txt = " | ".join(pending[:3]) if pending else "ver completion_criteria"
    checks = build_critical_questions(state)
    checks_txt = " ".join(checks[:6]) if checks else ""
    lab = _lab_focus(state)
    active = state.get("active_lab")
    active_txt = f"active_lab={active}." if active else "active_lab=null."
    return _safe_text(
        f"OBJETIVO MCP INCOMPLETO - continuar sin pedir permiso. "
        f"Leer {SKILL_REL} y {STATE_REL.as_posix()}. "
        f"objective_met=false. {active_txt} "
        f"Foco: {focus}. Blockers: {blocker_txt}. "
        f"Pendiente: {pending_txt}. Siguiente: {lab}. "
        f"Auto-check: {checks_txt}. "
        f"Narrar en chat antes de cada tool GUI (action-narration.md). "
        f"Solo tools MCP agenticas. Screenshot en hitos. Actualizar last_cycle al cerrar."
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

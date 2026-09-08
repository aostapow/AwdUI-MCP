"""Inject Teams harness state into state.json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".cursor/mcp-improvement-cycle/state.json"

TE_IDS = [
    ("TE-00", "Hooks + sesión MCP"),
    ("TE-01", "Launch Teams limpio"),
    ("TE-02", "Discovery + mapa UIA"),
    ("TE-03", "Nav rail"),
    ("TE-04", "Buscar Nicolás Awamori"),
    ("TE-05", "Chat 1:1 lectura"),
    ("TE-06", "Compose sin enviar"),
    ("TE-07", "Enviar a Awamori"),
    ("TE-08", "Scroll historial"),
    ("TE-09", "Equipos/canales lectura"),
    ("TE-10", "Calendario"),
    ("TE-11", "Llamadas UI"),
    ("TE-12", "Configuración"),
    ("TE-13", "Actividad"),
    ("TE-14", "Nuevo chat cancel"),
    ("TE-15", "Adjuntar cancel"),
    ("TE-16", "Emoji dismiss"),
    ("TE-17", "Atajos teclado"),
    ("TE-18", "Recovery stale"),
    ("TE-19", "Session health"),
    ("TE-20", "Cierre sesión"),
]

ARCHIVE_TE = ".cursor/mcp-improvement-cycle/runs/archive/legacy-skills/teams/flows"

FLOW_FILE = {
    "TE-00": "TE-00-hooks-session.md",
    "TE-01": "TE-01-launch.md",
    "TE-02": "TE-02-discovery.md",
    "TE-03": "TE-03-nav-rail.md",
    "TE-04": "TE-04-search-awamori.md",
    "TE-05": "TE-05-chat-readonly.md",
    "TE-06": "TE-06-compose-no-send.md",
    "TE-07": "TE-07-send-awamori.md",
    "TE-08": "TE-08-scroll-history.md",
    "TE-09": "TE-09-teams-channels.md",
    "TE-10": "TE-10-calendar.md",
    "TE-11": "TE-11-calls-ui.md",
    "TE-12": "TE-12-settings.md",
    "TE-13": "TE-13-activity.md",
    "TE-14": "TE-14-new-chat-cancel.md",
    "TE-15": "TE-15-attach-cancel.md",
    "TE-16": "TE-16-emoji-dismiss.md",
    "TE-17": "TE-17-keyboard-shortcuts.md",
    "TE-18": "TE-18-stale-recovery.md",
    "TE-19": "TE-19-session-health.md",
    "TE-20": "TE-20-session-close.md",
}


def main() -> None:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    state["goal"] = (
        "Auditoría agentica: 87 tools MCP + detección UIA/patterns — "
        "Calculadora + Notepad + Teams"
    )
    state["lab_apps"] = [
        "Windows Calculator (UWP)",
        "Bloc de notas (Notepad)",
        "Microsoft Teams (Electron)",
    ]
    state["teams_perfect"] = False
    state["objective_met"] = False
    state["current_focus"] = "Teams harness TE-00 — hooks + sesión MCP (sin envío hasta TE-07 Awamori)"
    state["teams_run"] = {
        "run_id": "teams-2026-09-06-start",
        "started_at": "2026-09-06T23:25:00Z",
        "locale": "es-AR",
        "protocol": "OBS→ACT→VERIFY + screenshot hitos; mensajes solo Nicolás Awamori TE-07",
        "progress": {"met": 0, "partial": 0, "pending": 21, "total": 21},
    }
    state["teams_matrix"] = {
        tid: {
            "status": "pending",
            "name": name,
            "flow": f"{ARCHIVE_TE}/{FLOW_FILE[tid]}",
        }
        for tid, name in TE_IDS
    }
    state["teams_matrix"]["TE-07"]["message_policy"] = "solo nicolas.awamori; prefijo [AwdUI-MCP-TE]"
    state["teams_matrix_progress"] = {
        "met": 0,
        "partial": 0,
        "pending": 21,
        "total": 21,
    }
    state["teams_run_plan"] = {
        tid: {
            "name": name,
            "status": "pending",
            "flow": FLOW_FILE[tid],
        }
        for tid, name in TE_IDS
    }
    state["teams_evidence"] = []
    state["teams_skill"] = ".cursor/skills/awdui-mcp-automejora/references/evaluacion-lab.md"
    state["teams_harness_skill"] = ".cursor/skills/awdui-mcp-automejora/references/evaluacion-lab.md"
    blockers = list(state.get("blockers") or [])
    teams_blocker = "Teams harness 0/21 — completar TE-02 discovery antes de TE-07 envío Awamori"
    if teams_blocker not in blockers:
        blockers.insert(0, teams_blocker)
    state["blockers"] = blockers
    state["last_cycle"] = {
        "ts": "2026-09-06T23:25:00Z",
        "work": "Armar skill + 21 flujos TE-00..TE-20 Teams; hooks activados",
        "live_verify": "pendiente TE-00 agentico",
        "next": "TE-00 hooks → TE-01 launch → TE-02 discovery (element-map)",
        "calculator_perfect": state.get("calculator_perfect"),
        "notepad_perfect": state.get("notepad_perfect"),
        "teams_perfect": False,
        "objective_met": False,
        "policy": "mensajes solo Nicolás Awamori en TE-07",
    }
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("state.json updated for Teams harness")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Full Calculator UIA catalog — all modes, roles, flyouts, panels.

Exit 0 only when every mode header is verified. Updates state.json.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "mcp-servers" / "awdui-server"
sys.path.insert(0, str(SERVER))
sys.path.insert(0, str(ROOT))
os.environ.setdefault("AWDUI_SKIP_VIRTUAL_DESKTOP", "1")

_VENV = Path.home() / ".awdui-mcp" / ".venv" / "Lib" / "site-packages"
if _VENV.is_dir():
    sys.path.insert(0, str(_VENV))

OUT = ROOT / "tests" / "integration" / "evidence" / "calculator_catalog.json"
STATE = ROOT / ".cursor" / "calculator-coverage" / "state.json"

MODE_ORDER = [
    "Standard", "Scientific", "Graphing", "Programmer", "Date",
    "Currency", "Volume", "Length",
]
EXTRA_MODES = ["SettingsItem"]
FLYOUT_BUTTONS = {
    "Scientific": ["trigButton", "funcButton"],
}


def _load_state() -> dict:
    if STATE.is_file():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {}


def _save_state(state: dict) -> None:
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _update_task(state: dict, task_id: str, status: str) -> None:
    for t in state.get("tasks", []):
        if t.get("id") == task_id:
            t["status"] = status
            break
    _save_state(state)


def _inventory_flyout(title: str, button_id: str) -> dict:
    from tests.integration.calculator_harness import click_button, inventory_all_elements

    click_button(automation_id=button_id, window_title=title)
    time.sleep(0.6)
    inv = inventory_all_elements(title, max_depth=8)
    buttons = inv.get("by_role", {}).get("Button", [])
    return {"trigger": button_id, "buttons": buttons, "button_count": len(buttons)}


def main() -> int:
    from tests.integration.gui_session import begin, end, require_supervised_session

    require_supervised_session("explore_calculator_full.py")
    begin(name="explore_calculator_full", max_clicks=400, max_seconds=900)

    failed_modes: list = []
    try:
        return _run_catalog()
    finally:
        try:
            from tests.integration.calculator_harness import teardown_calculator
            teardown_calculator()
        except Exception:
            pass
        end()


def _run_catalog() -> int:
    from tests.integration.calculator_harness import (
        ensure_calculator_running,
        get_current_mode,
        inventory_all_elements,
        inventory_buttons,
        switch_mode,
        click_button,
        close_navigation,
    )
    from tests.integration.evidence import capture_evidence

    state = _load_state()
    _update_task(state, "fix_switch_mode", "in_progress")

    ctx = ensure_calculator_running(timeout_s=30.0)
    if not ctx.get("success"):
        print(f"[FAIL] launch: {ctx.get('error')}")
        state.setdefault("blockers", []).append(ctx.get("error"))
        _save_state(state)
        return 1

    title = ctx["window_title"]
    catalog: dict = {
        "window_title": title,
        "explored_at": datetime.now(timezone.utc).isoformat(),
        "modes": {},
        "panels": {},
        "nav_items": [],
        "errors": [],
    }

    # --- Nav inventory (all ListItems) ---
    from tests.integration.calculator_harness import open_navigation
    from tools.ui_automation import do_list_elements

    open_navigation(title)
    nav_items = do_list_elements(window_title=title, max_depth=12, role="ListItem")
    for e in nav_items.get("elements", []):
        catalog["nav_items"].append({
            "automation_id": e.get("automation_id", ""),
            "name": e.get("name", ""),
        })
    close_navigation(title)
    print(f"[OK] nav_items={len(catalog['nav_items'])}")

    # --- Each mode ---
    failed_modes = []
    for mode_id in MODE_ORDER + EXTRA_MODES:
        print(f"[mode] {mode_id}...")
        sw = switch_mode(mode_id, window_title=title)
        if not sw.get("success"):
            err = f"{mode_id}: {sw.get('error')} header={sw.get('header')}"
            catalog["errors"].append(err)
            failed_modes.append(mode_id)
            print(f"  [FAIL] {err}")
            capture_evidence(f"mode_fail_{mode_id}", title)
            continue

        header = get_current_mode(title)
        inv = inventory_all_elements(title, max_depth=10)
        buttons = inventory_buttons(title)
        mode_entry = {
            "header": header,
            "switch": sw,
            "total_elements": inv.get("total", 0),
            "roles": inv.get("roles", []),
            "by_role": inv.get("by_role", {}),
            "buttons": buttons,
            "button_count": len(buttons),
            "flyouts": {},
        }

        for fly_id in FLYOUT_BUTTONS.get(mode_id, []):
            try:
                mode_entry["flyouts"][fly_id] = _inventory_flyout(title, fly_id)
                print(f"  [flyout] {fly_id} -> {mode_entry['flyouts'][fly_id]['button_count']} buttons")
            except Exception as exc:
                mode_entry["flyouts"][fly_id] = {"error": str(exc)}

        catalog["modes"][mode_id] = mode_entry
        print(f"  [OK] header={header!r} roles={inv.get('roles')} buttons={len(buttons)}")
        capture_evidence(f"mode_{mode_id}", title)

    _update_task(state, "fix_switch_mode", "done" if not failed_modes else "blocked")
    _update_task(state, "catalog_all_modes", "done" if not failed_modes else "blocked")

    # --- Panels ---
    switch_mode("Standard", window_title=title)
    for panel_id, key in [("HistoryButton", "history"), ("MemoryButton", "memory")]:
        print(f"[panel] {key}...")
        click_button(automation_id=panel_id, window_title=title)
        time.sleep(0.7)
        inv = inventory_all_elements(title, max_depth=8)
        catalog["panels"][key] = {
            "trigger": panel_id,
            "roles": inv.get("roles", []),
            "by_role": inv.get("by_role", {}),
        }
        capture_evidence(f"panel_{key}", title)
        # dismiss with escape
        from tools.input_tools import do_send_keys
        do_send_keys("escape")
        time.sleep(0.3)

    _update_task(state, "catalog_panels", "done")

    # --- Settings (separate mode) ---
    if "SettingsItem" in catalog["modes"]:
        _update_task(state, "catalog_settings", "done")
    else:
        _update_task(state, "catalog_settings", "blocked")

    if any(catalog["modes"].get(m, {}).get("flyouts") for m in FLYOUT_BUTTONS):
        _update_task(state, "catalog_flyouts", "done")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[OK] catalog -> {OUT}")
    print(f"  modes OK: {len(catalog['modes']) - len(failed_modes)}/{len(MODE_ORDER) + len(EXTRA_MODES)}")
    if catalog["errors"]:
        print(f"  errors: {catalog['errors']}")

    if failed_modes:
        state["status"] = "blocked"
        state["blockers"] = catalog["errors"]
        _save_state(state)
        return 1

    state["status"] = "catalog_complete"
    _save_state(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Borrar cola, corridas y punteros de lab de una app; no toca otras apps en state.json.

Usage:
  python scripts/reset_app_lab.py "Calculadora"
  python scripts/reset_app_lab.py "Calculadora" --dry-run
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from app_backlog_lib import (  # noqa: E402
    REPO_ROOT,
    RUNS_ROOT,
    STATE_PATH,
    app_dir,
    slug_from_app_name,
)

# Legacy top-level en state.json (matriz CAL-* histórica)
_CALC_LEGACY_KEYS = (
    "calculator_perfect",
    "calculator_run",
    "calculator_matrix",
    "calculator_evidence",
)


def _purge_calculator_scenarios_in_state(state: dict) -> list[str]:
    """Quita CAL-* de ast_skill_consultation y flags legacy."""
    removed: list[str] = []
    asc = state.get("ast_skill_consultation")
    if isinstance(asc, dict):
        for key in list(asc.keys()):
            if str(key).startswith("CAL-"):
                del asc[key]
                removed.append(str(key))
        if not asc:
            state.pop("ast_skill_consultation", None)
        else:
            state["ast_skill_consultation"] = asc
    for key in _CALC_LEGACY_KEYS:
        if key not in state:
            continue
        if key == "calculator_perfect":
            state[key] = False
            removed.append(f"{key}=false")
        else:
            state.pop(key, None)
            removed.append(key)
    return removed


def _run_dirs_for_slug(slug: str) -> list[Path]:
    if not RUNS_ROOT.is_dir():
        return []
    return sorted(
        p
        for p in RUNS_ROOT.iterdir()
        if p.is_dir() and p.name.startswith(f"{slug}-")
    )


def reset_app_lab(app_name: str, *, dry_run: bool = False) -> dict:
    slug = slug_from_app_name(app_name)
    removed_runs: list[str] = []
    removed_app_dir = False

    for run_path in _run_dirs_for_slug(slug):
        removed_runs.append(run_path.name)
        if not dry_run:
            shutil.rmtree(run_path, ignore_errors=True)

    app_path = app_dir(slug)
    if app_path.is_dir():
        removed_app_dir = True
        if not dry_run:
            shutil.rmtree(app_path, ignore_errors=True)

    state_patch: dict = {}
    if STATE_PATH.is_file() and not dry_run:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8-sig"))
        lab_apps = state.get("lab_apps") or {}
        if app_name in lab_apps:
            del lab_apps[app_name]
            state["lab_apps"] = lab_apps
        if state.get("active_lab") == app_name:
            state["active_lab"] = app_name
            state.pop("active_app_slug", None)
            state.pop("backlog_ref", None)
            state.pop("active_run", None)
        legacy_removed: list[str] = []
        if slug == "calculadora":
            legacy_removed = _purge_calculator_scenarios_in_state(state)
        state["current_focus"] = (
            f"{app_name}: lab reiniciado — ejecutar init_or_resume_app_backlog.py (solo hygiene)"
        )
        state["last_cycle"] = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "mode": "lab_reset",
            "focus": state["current_focus"],
            "observe": f"reset_app_lab slug={slug}",
            "act": f"removed runs={removed_runs} app_dir={removed_app_dir}",
            "verify": "ok" if not dry_run else "dry-run",
            "next": f'python scripts/init_or_resume_app_backlog.py "{app_name}"',
        }
        STATE_PATH.write_text(
            json.dumps(state, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8-sig",
        )
        state_patch = {
            "calculator_perfect": state.get("calculator_perfect"),
            "active_lab": state.get("active_lab"),
            "legacy_removed": legacy_removed,
        }
    else:
        legacy_removed = []

    return {
        "app_name": app_name,
        "app_slug": slug,
        "dry_run": dry_run,
        "removed_run_dirs": removed_runs,
        "removed_apps_dir": removed_app_dir,
        "apps_path": (
            str(app_path.relative_to(REPO_ROOT))
            if removed_app_dir
            and str(app_path).startswith(str(REPO_ROOT))
            else (str(app_path) if removed_app_dir else None)
        ),
        "state_patch": state_patch,
        "legacy_state_removed": legacy_removed if not dry_run else [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset lab artifacts for one app")
    parser.add_argument("app_name", help='e.g. "Calculadora"')
    parser.add_argument("--dry-run", action="store_true", help="List only, no deletes")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = reset_app_lab(args.app_name, dry_run=args.dry_run)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        action = "DRY-RUN" if result["dry_run"] else "RESET"
        print(f"{action} lab for {result['app_name']} (slug={result['app_slug']})")
        print(f"  runs removed: {result['removed_run_dirs'] or '(none)'}")
        print(f"  apps/{result['app_slug']}/ removed: {result['removed_apps_dir']}")
        if not result["dry_run"]:
            print(
                f'  next: python scripts/init_or_resume_app_backlog.py "{args.app_name}"'
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

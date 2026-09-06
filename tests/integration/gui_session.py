"""Supervised GUI session — prevents orphan scripts from hijacking mouse/keyboard.

During MCP learning phase, coordinate input must be:
1. Initiated with AWDUI_GUI_SESSION set (agent-supervised run)
2. Target window verified alive before each click
3. Bounded by click budget and wall-clock timeout
4. Cleaned up on exit (atexit + lock file removal)
"""
from __future__ import annotations

import atexit
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

_LOCK_DIR = Path.home() / ".awdui-mcp"
_LOCK_FILE = _LOCK_DIR / "gui_session.lock"
_DEFAULT_MAX_CLICKS = 80
_DEFAULT_MAX_SECONDS = 300

_state: dict = {}


def _read_lock() -> Optional[dict]:
    if not _LOCK_FILE.is_file():
        return None
    try:
        return json.loads(_LOCK_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_lock(data: dict) -> None:
    _LOCK_DIR.mkdir(parents=True, exist_ok=True)
    _LOCK_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def clear_lock() -> None:
    try:
        _LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def require_supervised_session(script_name: str) -> None:
    """Refuse to run unattended GUI automation scripts."""
    if not os.environ.get("AWDUI_GUI_SESSION"):
        msg = (
            f"BLOCKED: {script_name} moves the real mouse and requires "
            f"AWDUI_GUI_SESSION=1 set by a supervising agent in the foreground. "
            f"Do not run in background. Prefer MCP tools (click_element) per step."
        )
        print(msg, file=sys.stderr)
        raise SystemExit(2)


def begin(
    *,
    name: str = "harness",
    window_title: str = "",
    max_clicks: int = _DEFAULT_MAX_CLICKS,
    max_seconds: float = _DEFAULT_MAX_SECONDS,
) -> dict:
    """Start supervised session; abort if another lock is active."""
    if _state.get("started_at") and _state.get("pid") == os.getpid():
        if window_title:
            _state["window_title"] = window_title
        _state["max_clicks"] = max(int(_state.get("max_clicks", 0)), max_clicks)
        _state["max_seconds"] = max(float(_state.get("max_seconds", 0)), max_seconds)
        _write_lock({**_state})
        return dict(_state)

    existing = _read_lock()
    if existing and existing.get("pid") != os.getpid():
        age = time.time() - float(existing.get("started_at", 0))
        if age < float(existing.get("max_seconds", _DEFAULT_MAX_SECONDS)):
            raise RuntimeError(
                f"GUI session already active (pid={existing.get('pid')}, "
                f"name={existing.get('name')}). Run scripts/stop_gui_session.ps1 first."
            )
        clear_lock()

    _state.update({
        "name": name,
        "pid": os.getpid(),
        "window_title": window_title,
        "started_at": time.time(),
        "max_clicks": max_clicks,
        "max_seconds": max_seconds,
        "click_count": 0,
    })
    _write_lock(_state.copy())
    atexit.register(end)
    return dict(_state)


def end() -> None:
    clear_lock()
    try:
        from tests.integration.calculator_harness import clear_calc_target
        clear_calc_target()
    except Exception:
        pass


def _assert_active() -> None:
    if not _state.get("started_at"):
        raise RuntimeError("GUI session not started — call gui_session.begin() first")
    elapsed = time.time() - float(_state["started_at"])
    if elapsed > float(_state.get("max_seconds", _DEFAULT_MAX_SECONDS)):
        end()
        raise RuntimeError(f"GUI session timed out after {elapsed:.0f}s")
    if int(_state.get("click_count", 0)) >= int(_state.get("max_clicks", _DEFAULT_MAX_CLICKS)):
        end()
        raise RuntimeError("GUI session click budget exhausted")


def calculator_window_alive(window_title: str) -> bool:
    from tools.windows import do_list_windows

    if not window_title:
        return False
    hint = window_title.lower()
    for w in do_list_windows():
        title = (w.get("title") or "").lower()
        proc = (w.get("process_name") or "").lower()
        if hint in title and "calculatorapp" in proc:
            return True
        if hint in title and "applicationframehost" in proc:
            return True
    return False


def guarded_click(x: int, y: int, *, window_title: str = "", reason: str = "") -> dict:
    """Click only if supervised session active and target window exists."""
    wt = window_title or _state.get("window_title") or ""
    if not _state.get("started_at"):
        if os.environ.get("AWDUI_GUI_SESSION") or os.environ.get("PYTEST_CURRENT_TEST"):
            begin(name="auto", window_title=wt)
        else:
            raise RuntimeError(
                "guarded_click requires gui_session.begin() or MCP tools for agentic control"
            )
    _assert_active()
    wt = window_title or _state.get("window_title") or ""
    if wt and not calculator_window_alive(wt):
        end()
        raise RuntimeError(
            f"ABORT: target window '{wt}' no longer open — refusing click at ({x},{y}). "
            f"reason={reason}"
        )

    from tools.input_tools import do_click
    result = do_click(x, y)
    _state["click_count"] = int(_state.get("click_count", 0)) + 1
    _write_lock({**_state})
    return result

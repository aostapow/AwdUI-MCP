"""Persistent FlaUI event sidecar bridge (native UIA event handlers)."""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Optional

_SIDECAR_PATH = (
    Path(__file__).resolve().parents[2]
    / "awdui-event-sidecar"
    / "publish"
    / "awdui-event-sidecar.exe"
)

_proc: Optional[subprocess.Popen[str]] = None
_reader: Optional[threading.Thread] = None
_io_lock = threading.Lock()
_req_lock = threading.Lock()
_req_id = 0
_pending: dict[int, dict[str, Any]] = {}
_native_sessions: set[str] = set()


def sidecar_available() -> bool:
    return sys.platform == "win32" and _SIDECAR_PATH.is_file()


def _next_id() -> int:
    global _req_id
    with _req_lock:
        _req_id += 1
        return _req_id


def _reader_loop() -> None:
    global _proc
    proc = _proc
    if proc is None or proc.stdout is None:
        return
    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        try:
            resp = json.loads(line)
        except json.JSONDecodeError:
            continue
        rid = resp.get("id")
        if rid is None:
            continue
        with _io_lock:
            slot = _pending.get(int(rid))
            if slot is not None:
                slot["response"] = resp
                slot["event"].set()


def _ensure_server() -> bool:
    global _proc, _reader
    if not sidecar_available():
        return False
    with _io_lock:
        if _proc is not None and _proc.poll() is None:
            return True
        try:
            _proc = subprocess.Popen(
                [str(_SIDECAR_PATH), "--server"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        except OSError:
            _proc = None
            return False
        _reader = threading.Thread(target=_reader_loop, daemon=True, name="awdui-event-sidecar-reader")
        _reader.start()
        ping = _call("ping", {}, timeout=5.0)
        return bool(ping.get("success"))


def _call(command: str, params: dict[str, Any], timeout: float = 10.0) -> dict[str, Any]:
    if not _ensure_server():
        return {"success": False, "error": "event sidecar not available"}
    proc = _proc
    if proc is None or proc.stdin is None:
        return {"success": False, "error": "event sidecar process missing"}

    rid = _next_id()
    slot = {"event": threading.Event(), "response": None}
    with _io_lock:
        _pending[rid] = slot
    payload = json.dumps({"id": rid, "command": command, "params": params}, ensure_ascii=False)
    try:
        with _io_lock:
            proc.stdin.write(payload + "\n")
            proc.stdin.flush()
    except OSError as exc:
        with _io_lock:
            _pending.pop(rid, None)
        return {"success": False, "error": str(exc)}

    if not slot["event"].wait(timeout):
        with _io_lock:
            _pending.pop(rid, None)
        return {"success": False, "error": "event sidecar timeout"}

    with _io_lock:
        resp = slot["response"] or {}
        _pending.pop(rid, None)
    if resp.get("error"):
        return {"success": False, "error": resp.get("error")}
    return resp


def _enrich_params(
    window_title: Optional[str],
    window_handle: Optional[int],
    automation_id: Optional[str],
    name: Optional[str],
) -> dict[str, Any]:
    from tools.target_window import get_target
    from tools.windows import resolve_window_handle

    params: dict[str, Any] = {}
    title = (window_title or get_target() or "").strip()
    if title:
        params["window_title"] = title
    hwnd = int(window_handle or 0) or resolve_window_handle(title) or 0
    if hwnd:
        params["hwnd"] = hwnd
    if automation_id:
        params["automation_id"] = automation_id
    if name:
        params["name"] = name
    return params


def start_native_monitor(
    session_id: str,
    event_type: str,
    automation_id: Optional[str] = None,
    name: Optional[str] = None,
    window_title: Optional[str] = None,
    window_handle: Optional[int] = None,
) -> dict[str, Any]:
    params = _enrich_params(window_title, window_handle, automation_id, name)
    params["session_id"] = session_id
    params["event_type"] = event_type
    resp = _call("monitor_start", params)
    if resp.get("success"):
        _native_sessions.add(session_id)
    return resp


def get_native_events(session_id: str, max_count: int = 100) -> dict[str, Any]:
    return _call(
        "monitor_get_events",
        {"session_id": session_id, "max_count": max_count},
    )


def stop_native_monitor(session_id: Optional[str] = None) -> dict[str, Any]:
    if session_id:
        resp = _call("monitor_stop", {"session_id": session_id})
        _native_sessions.discard(session_id)
        return resp
    resp = _call("monitor_stop_all", {})
    _native_sessions.clear()
    return resp


def is_native_session(session_id: str) -> bool:
    return session_id in _native_sessions


def shutdown_sidecar() -> None:
    global _proc, _reader
    try:
        if _native_sessions:
            _call("monitor_stop_all", {}, timeout=3.0)
    except Exception:
        pass
    _native_sessions.clear()
    with _io_lock:
        proc = _proc
        _proc = None
    if proc is not None and proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    _reader = None

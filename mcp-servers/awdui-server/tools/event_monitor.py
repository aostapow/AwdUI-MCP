"""UIA event monitoring — native FlaUI handlers with poll fallback."""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Optional

_MAX_EVENTS = 500
_sessions: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def _session_snapshot(
    automation_id: Optional[str],
    name: Optional[str],
    window_title: Optional[str],
    window_handle: Optional[int],
) -> dict[str, Any]:
    snap: dict[str, Any] = {"focused": None, "hash": "", "property": None}
    try:
        from tools.ui_automation import do_get_focused_element, do_ui_fingerprint, do_read_element

        focused = do_get_focused_element()
        if focused.get("found"):
            snap["focused"] = focused.get("element") or focused.get("properties")
        fp = do_ui_fingerprint(window_title=window_title)
        snap["hash"] = fp.get("hash", "")
        if automation_id or name:
            read = do_read_element(
                automation_id=automation_id,
                name=name,
                window_title=window_title,
                window_handle=window_handle,
            )
            if read.get("success"):
                snap["property"] = read.get("properties")
    except Exception as exc:
        snap["error"] = str(exc)
    return snap


def _monitor_loop(session_id: str) -> None:
    with _lock:
        session = _sessions.get(session_id)
    if not session:
        return

    poll_s = max(0.1, float(session.get("poll_ms", 200)) / 1000.0)
    event_type = (session.get("event_type") or "focus").lower()
    last = session.get("last_snapshot") or {}

    while not session.get("stop_event").is_set():
        current = _session_snapshot(
            session.get("automation_id"),
            session.get("name"),
            window_title=session.get("window_title"),
            window_handle=session.get("window_handle"),
        )
        events = session.setdefault("events", [])

        if event_type in ("focus", "focuschanged"):
            prev = (last.get("focused") or {}).get("automation_id") or (last.get("focused") or {}).get("name")
            cur = (current.get("focused") or {}).get("automation_id") or (current.get("focused") or {}).get("name")
            if cur and cur != prev:
                events.append(
                    {
                        "type": "focus",
                        "timestamp": time.time(),
                        "detail": current.get("focused"),
                    }
                )
        elif event_type in ("structurechanged", "structure"):
            if current.get("hash") and current.get("hash") != last.get("hash"):
                events.append(
                    {
                        "type": "structurechanged",
                        "timestamp": time.time(),
                        "hash": current.get("hash"),
                    }
                )
        elif event_type in ("propertychanged", "property"):
            if current.get("property") != last.get("property"):
                events.append(
                    {
                        "type": "propertychanged",
                        "timestamp": time.time(),
                        "properties": current.get("property"),
                    }
                )

        if len(events) > _MAX_EVENTS:
            del events[: len(events) - _MAX_EVENTS]
        session["last_snapshot"] = current
        time.sleep(poll_s)


def _start_poll_session(
    session_id: str,
    event_type: str,
    automation_id: Optional[str],
    name: Optional[str],
    window_title: Optional[str],
    window_handle: Optional[int],
    poll_ms: int,
) -> dict[str, Any]:
    stop_event = threading.Event()
    session = {
        "session_id": session_id,
        "backend": "poll",
        "event_type": event_type,
        "automation_id": automation_id or "",
        "name": name or "",
        "window_title": window_title or "",
        "window_handle": int(window_handle or 0),
        "poll_ms": max(50, int(poll_ms or 200)),
        "stop_event": stop_event,
        "events": [],
        "last_snapshot": {},
        "started_at": time.time(),
    }
    with _lock:
        _sessions[session_id] = session
    thread = threading.Thread(
        target=_monitor_loop,
        args=(session_id,),
        daemon=True,
        name=f"awdui-event-monitor-{session_id}",
    )
    session["thread"] = thread
    thread.start()
    return session


def do_start_event_monitor(
    event_type: str,
    automation_id: Optional[str] = None,
    name: Optional[str] = None,
    window_title: Optional[str] = None,
    window_handle: Optional[int] = None,
    poll_ms: int = 200,
) -> dict[str, Any]:
    session_id = uuid.uuid4().hex[:12]
    event_type_norm = (event_type or "focus").lower()

    try:
        from tools.event_sidecar_bridge import sidecar_available, start_native_monitor

        if sidecar_available():
            native = start_native_monitor(
                session_id=session_id,
                event_type=event_type_norm,
                automation_id=automation_id,
                name=name,
                window_title=window_title,
                window_handle=window_handle,
            )
            if native.get("success"):
                with _lock:
                    _sessions[session_id] = {
                        "session_id": session_id,
                        "backend": "flaui_native",
                        "event_type": event_type_norm,
                        "automation_id": automation_id or "",
                        "name": name or "",
                        "window_title": window_title or "",
                        "window_handle": int(window_handle or 0),
                        "poll_ms": 0,
                        "started_at": time.time(),
                        "events": [],
                    }
                return {
                    "success": True,
                    "session_id": session_id,
                    "event_type": event_type_norm,
                    "backend": "flaui_native",
                    "poll_ms": 0,
                }
    except Exception:
        pass

    session = _start_poll_session(
        session_id,
        event_type_norm,
        automation_id,
        name,
        window_title,
        window_handle,
        poll_ms,
    )
    return {
        "success": True,
        "session_id": session_id,
        "event_type": session["event_type"],
        "backend": "poll",
        "poll_ms": session["poll_ms"],
    }


def do_stop_event_monitor(session_id: Optional[str] = None) -> dict[str, Any]:
    stopped: list[str] = []
    native_ids: list[str] = []
    with _lock:
        targets = [session_id] if session_id else list(_sessions.keys())
        for sid in targets:
            session = _sessions.get(sid)
            if not session:
                continue
            if session.get("backend") == "flaui_native":
                native_ids.append(sid)
            else:
                stop_ev = session.get("stop_event")
                if stop_ev is not None:
                    stop_ev.set()
            stopped.append(sid)
            _sessions.pop(sid, None)

    if native_ids:
        try:
            from tools.event_sidecar_bridge import stop_native_monitor

            for sid in native_ids:
                stop_native_monitor(sid)
            if session_id is None:
                stop_native_monitor(None)
        except Exception:
            pass

    return {"success": True, "stopped": stopped, "count": len(stopped)}


def do_get_event_log(
    session_id: Optional[str] = None,
    max_count: int = 100,
) -> dict[str, Any]:
    max_count = max(1, min(int(max_count or 100), _MAX_EVENTS))
    with _lock:
        if session_id:
            session = _sessions.get(session_id)
            if not session:
                return {"success": False, "error": f"unknown session: {session_id}"}
            backend = session.get("backend", "poll")
            if backend == "flaui_native":
                try:
                    from tools.event_sidecar_bridge import get_native_events

                    native = get_native_events(session_id, max_count=max_count)
                    if native.get("success"):
                        return {
                            "success": True,
                            "session_id": session_id,
                            "count": native.get("count", 0),
                            "events": native.get("events", []),
                            "active_sessions": len(_sessions),
                            "backend": "flaui_native",
                        }
                    return {
                        "success": False,
                        "error": native.get("error", "native get_event_log failed"),
                    }
                except Exception as exc:
                    return {"success": False, "error": str(exc)}
            events = list(session.get("events") or [])
        else:
            events = []
            for sid, session in list(_sessions.items()):
                if session.get("backend") == "flaui_native":
                    try:
                        from tools.event_sidecar_bridge import get_native_events

                        native = get_native_events(sid, max_count=max_count)
                        if native.get("success"):
                            events.extend(native.get("events") or [])
                    except Exception:
                        pass
                else:
                    events.extend(session.get("events") or [])

    events = events[-max_count:]
    return {
        "success": True,
        "session_id": session_id or "",
        "count": len(events),
        "events": events,
        "active_sessions": len(_sessions),
    }


def register(server) -> int:
    from tools.params import resolve_window_title as _wt
    from tools.safety import ActionTimeoutError, with_timeout

    @server.tool()
    def start_event_monitor(
        event_type: str = "focus",
        automation_id: str = "",
        name: str = "",
        window_title: str = "",
        title: str = "",
        window_handle: int = 0,
        poll_ms: int = 200,
    ) -> str:
        """Start monitoring UIA events (focus, structurechanged, propertychanged).

        Uses native FlaUI event handlers when the event sidecar is built; otherwise poll fallback.
        Returns session_id; poll events with get_event_log; stop with stop_event_monitor.
        """
        try:
            result = with_timeout(
                lambda: do_start_event_monitor(
                    event_type=event_type,
                    automation_id=automation_id or None,
                    name=name or None,
                    window_title=_wt(window_title, title),
                    window_handle=window_handle or None,
                    poll_ms=poll_ms,
                ),
                timeout=10.0,
            )
        except ActionTimeoutError as exc:
            return f"ERROR: {exc}"
        backend = result.get("backend", "poll")
        poll = result.get("poll_ms", poll_ms)
        return (
            f"OK session_id={result.get('session_id')} "
            f"event_type={result.get('event_type')} backend={backend} poll_ms={poll}"
        )

    @server.tool()
    def stop_event_monitor(session_id: str = "") -> str:
        """Stop one event monitor session (or all if session_id omitted)."""
        result = do_stop_event_monitor(session_id or None)
        return f"OK stopped={result.get('count', 0)} sessions={result.get('stopped', [])}"

    @server.tool()
    def get_event_log(session_id: str = "", max_count: int = 100) -> str:
        """Return captured UIA monitor events for a session."""
        import json

        result = do_get_event_log(session_id=session_id or None, max_count=max_count)
        if not result.get("success"):
            return result.get("error", "get_event_log failed")
        return json.dumps(result, ensure_ascii=False)

    return 3

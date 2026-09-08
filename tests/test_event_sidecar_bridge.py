"""Tests for native UIA event sidecar bridge."""
from __future__ import annotations

from unittest import mock


def test_start_event_monitor_native_backend():
    with mock.patch("tools.event_sidecar_bridge.sidecar_available", return_value=True):
        with mock.patch(
            "tools.event_sidecar_bridge.start_native_monitor",
            return_value={"success": True, "backend": "flaui_native", "session_id": "abc123"},
        ):
            with mock.patch(
                "tools.event_monitor._start_poll_session",
            ) as poll_mock:
                from tools.event_monitor import _sessions, do_start_event_monitor

                out = do_start_event_monitor(event_type="focus")
                sid = out.get("session_id")
                if sid:
                    _sessions.pop(sid, None)
    assert out["success"]
    assert out["backend"] == "flaui_native"
    poll_mock.assert_not_called()


def test_start_event_monitor_falls_back_when_native_times_out():
    import time

    def slow_start(*_a, **_k):
        time.sleep(10)
        return {"success": True}

    with mock.patch("tools.event_sidecar_bridge.sidecar_available", return_value=True):
        with mock.patch("tools.event_sidecar_bridge.start_native_monitor", side_effect=slow_start):
            with mock.patch("tools.event_monitor._start_poll_session") as poll_mock:
                poll_mock.return_value = {
                    "session_id": "poll1",
                    "backend": "poll",
                    "event_type": "focus",
                    "poll_ms": 200,
                }
                from tools.event_monitor import do_start_event_monitor

                out = do_start_event_monitor(event_type="focus", poll_ms=100)
    assert out["success"]
    assert out["backend"] == "poll"
    poll_mock.assert_called_once()


def test_get_event_log_native_delegates():
    with mock.patch("tools.event_sidecar_bridge.get_native_events") as native_get:
        native_get.return_value = {
            "success": True,
            "count": 1,
            "events": [{"type": "focus"}],
            "backend": "flaui_native",
        }
        from tools.event_monitor import _sessions, do_get_event_log

        _sessions["sess1"] = {"session_id": "sess1", "backend": "flaui_native", "events": []}
        try:
            out = do_get_event_log(session_id="sess1", max_count=5)
        finally:
            _sessions.pop("sess1", None)
    assert out["success"]
    assert out["backend"] == "flaui_native"
    assert out["count"] == 1
    native_get.assert_called_once()


def test_stop_event_monitor_native():
    with mock.patch("tools.event_sidecar_bridge.stop_native_monitor") as native_stop:
        from tools.event_monitor import _sessions, do_stop_event_monitor

        _sessions["sess2"] = {"session_id": "sess2", "backend": "flaui_native"}
        try:
            out = do_stop_event_monitor("sess2")
        finally:
            _sessions.pop("sess2", None)
    assert out["success"]
    native_stop.assert_called_with("sess2")


def test_ensure_server_ping_without_deadlock():
    """_ensure_server must not call _call while holding _io_lock (non-reentrant deadlock)."""
    import tools.event_sidecar_bridge as bridge

    bridge.shutdown_sidecar()
    fake_proc = mock.MagicMock()
    fake_proc.poll.return_value = None
    fake_proc.stdin = mock.MagicMock()
    fake_proc.stdout = iter(['{"id": 1, "success": true, "backend": "flaui_native"}\n'])
    with mock.patch.object(bridge, "sidecar_available", return_value=True):
        with mock.patch.object(bridge.subprocess, "Popen", return_value=fake_proc):
            ok = bridge._ensure_server()
    assert ok is True
    bridge.shutdown_sidecar()

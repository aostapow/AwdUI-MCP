"""Tests for D1-D5 winapp parity tools."""
from __future__ import annotations

from unittest import mock


def test_fill_form_success():
    with mock.patch("tools.ui_automation.do_set_element_value") as mock_set:
        mock_set.return_value = {"success": True}
        from tools.form_tools import do_fill_form

        result = do_fill_form(
            [{"automation_id": "txtA", "value": "hello"}, {"name": "FieldB", "value": "42"}]
        )
        assert result["success"]
        assert result["filled"] == 2


def test_get_all_values_collect():
    from detection.form_read import collect_all_values

    payload = collect_all_values(
        [
            {"role": "Edit", "automation_id": "txtA", "name": "A", "value": "hello"},
            {"role": "Button", "automation_id": "btn", "name": "Go"},
        ]
    )
    assert payload["count"] == 1
    assert payload["values"]["txtA"]["value"] == "hello"


def test_find_all_elements_indexes():
    with mock.patch("tools.ui_automation.do_find_element") as mock_find:
        mock_find.return_value = {
            "found": True,
            "elements": [{"role": "Button", "name": "A"}, {"role": "Button", "name": "B"}],
        }
        from tools.element_read_tools import do_find_all_elements

        out = do_find_all_elements(automation_id="dup")
        assert out["count"] == 2
        assert out["elements"][1]["index"] == 1


def test_read_element_by_index():
    with mock.patch("tools.ui_automation.do_get_element_properties") as mock_props:
        mock_props.return_value = {"found": False}
        with mock.patch("tools.element_read_tools.do_find_all_elements") as mock_all:
            mock_all.return_value = {
                "elements": [{"role": "Edit", "name": "A", "value": "1"}],
            }
            from tools.element_read_tools import do_read_element_by_index

            out = do_read_element_by_index(index=0, automation_id="txt")
            assert out["success"]
            assert out["properties"]["value"] == "1"


def test_get_snapshot():
    with mock.patch("tools.ui_automation.do_list_elements") as mock_list:
        mock_list.return_value = {
            "elements": [
                {
                    "role": "Button",
                    "name": "OK",
                    "automation_id": "btn",
                    "x": 1,
                    "y": 2,
                    "width": 3,
                    "height": 4,
                }
            ],
            "count": 1,
            "backend_used": "uia",
        }
        from tools.element_read_tools import do_get_snapshot

        out = do_get_snapshot(max_depth=2)
        assert out["success"]
        assert out["count"] == 1


def test_event_monitor_lifecycle():
    with mock.patch("tools.event_sidecar_bridge.sidecar_available", return_value=False):
        with mock.patch(
            "tools.event_monitor._session_snapshot",
            return_value={"focused": {"name": "A"}, "hash": "h1"},
        ):
            import time

            from tools.event_monitor import (
                do_get_event_log,
                do_start_event_monitor,
                do_stop_event_monitor,
            )

            started = do_start_event_monitor(event_type="focus", poll_ms=50)
            assert started["success"]
            assert started.get("backend") == "poll"
            sid = started["session_id"]
            time.sleep(0.15)
            log = do_get_event_log(session_id=sid, max_count=10)
            assert log["success"]
            stopped = do_stop_event_monitor(sid)
            assert stopped["success"]


def test_check_session_enriched():
    with mock.patch("tools.target_window.get_target", return_value="AST"):
        with mock.patch("tools.windows.resolve_window_handle", return_value=100):
            with mock.patch("tools.session_tools._window_minimized", return_value=True):
                with mock.patch("tools.session_tools._workstation_locked", return_value=False):
                    from tools.session_tools import do_check_session_status

                    out = do_check_session_status()
    assert out["target_minimized"] is True
    assert out["operations_available"]["click"] is False


def test_resolve_hwnd_invalid():
    from detection.hwnd_scope import resolve_window_from_hwnd

    out = resolve_window_from_hwnd(0)
    assert not out["success"]
    assert "Invalid" in out["error"]

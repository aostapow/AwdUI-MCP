"""Tests for target app scope enforcement."""
from tools.target_scope import (
    get_scoped_windows,
    get_target_process_ids,
    validate_element_in_scope,
    validate_point_in_scope,
)


def _win(title, pid=42, x=100, y=100, w=800, h=600):
    return {
        "title": title,
        "process_id": pid,
        "process_name": "ast.exe",
        "x": x,
        "y": y,
        "width": w,
        "height": h,
    }


def test_get_target_process_ids(monkeypatch):
    monkeypatch.setattr("tools.target_window.get_target", lambda: "AST")
    monkeypatch.setattr(
        "tools.windows.do_list_windows",
        lambda: [_win("AST - Activities Manager", pid=99)],
    )
    monkeypatch.setattr(
        "tools.windows.find_matching_window",
        lambda t, w: {"window": w[0]},
    )
    assert get_target_process_ids() == {99}


def test_validate_point_inside_scope(monkeypatch):
    monkeypatch.setattr("tools.target_window.get_target", lambda: "AST")
    monkeypatch.setattr(
        "tools.windows.do_list_windows",
        lambda: [_win("AST", pid=42, x=100, y=100, w=400, h=300)],
    )
    monkeypatch.setattr(
        "tools.windows.find_matching_window",
        lambda t, w: {"window": w[0]},
    )
    ok, err = validate_point_in_scope(200, 200)
    assert ok is True
    assert err == ""


def test_validate_point_outside_scope_blocked(monkeypatch):
    monkeypatch.setattr("tools.target_window.get_target", lambda: "AST")
    monkeypatch.setattr(
        "tools.windows.do_list_windows",
        lambda: [_win("AST", pid=42, x=100, y=100, w=400, h=300)],
    )
    monkeypatch.setattr(
        "tools.windows.find_matching_window",
        lambda t, w: {"window": w[0]},
    )
    ok, err = validate_point_in_scope(10, 10)
    assert ok is False
    assert "blocked" in err.lower()


def test_validate_element_wrong_pid(monkeypatch):
    monkeypatch.setattr("tools.target_window.get_target", lambda: "AST")
    monkeypatch.setattr(
        "tools.windows.do_list_windows",
        lambda: [_win("AST", pid=42)],
    )
    monkeypatch.setattr(
        "tools.windows.find_matching_window",
        lambda t, w: {"window": w[0]},
    )
    elem = {
        "automation_id": "teFind",
        "process_id": 9999,
        "x": 200,
        "y": 200,
        "width": 100,
        "height": 20,
    }
    ok, err = validate_element_in_scope(elem)
    assert ok is False
    assert "9999" in err


def test_no_target_no_restriction(monkeypatch):
    monkeypatch.setattr("tools.target_window.get_target", lambda: None)
    assert get_target_process_ids() is None
    ok, err = validate_point_in_scope(0, 0)
    assert ok is True

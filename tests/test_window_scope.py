"""Tests for MDI / child window scope resolution."""
from tools.window_scope import resolve_window_scope


def _win(title, pid=100, proc="app.exe", x=0, y=0):
    return {
        "title": title,
        "process_id": pid,
        "process_name": proc,
        "x": x,
        "y": y,
        "width": 800,
        "height": 600,
    }


def test_resolve_direct_match(monkeypatch):
    windows = [_win("AST - Activities Manager")]
    monkeypatch.setattr("tools.windows.do_list_windows", lambda: windows)
    monkeypatch.setattr(
        "tools.windows.find_matching_window",
        lambda t, w: {"window": w[0], "match_quality": "exact"},
    )
    result = resolve_window_scope("AST")
    assert result["window"]["title"] == "AST - Activities Manager"
    assert result["scoped"] == "direct"


def test_resolve_mdi_child_fallback(monkeypatch):
    parent = _win("AST - Activities Manager", pid=42)
    child = _win("Carga de Horas - AST", pid=42)
    windows = [parent, child]

    def fake_match(title, wins):
        if "carga" in title.lower():
            return {"window": None, "available": [w["title"] for w in wins]}
        if "ast" in title.lower():
            return {"window": parent, "match_quality": "exact"}
        return {"window": None, "available": []}

    monkeypatch.setattr("tools.windows.do_list_windows", lambda: windows)
    monkeypatch.setattr("tools.windows.find_matching_window", fake_match)
    monkeypatch.setattr("tools.target_window.get_target", lambda: "AST")

    result = resolve_window_scope("Carga de Horas")
    assert result["scoped"] == "mdi_child"
    assert result["window"]["title"] == "Carga de Horas - AST"
    assert result["parent_title"] == "AST - Activities Manager"

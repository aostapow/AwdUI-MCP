"""Tests for observe_ui depth/element caps."""
from detection.discovery.observer import observe_ui


def test_observe_ui_caps_tree_sample(monkeypatch):
    many = [{"name": f"e{i}", "role": "Button"} for i in range(200)]

    monkeypatch.setattr(
        "tools.framework_detect.do_detect_framework",
        lambda _wt: {"framework": "winforms"},
    )
    monkeypatch.setattr(
        "tools.ui_automation.do_ui_fingerprint",
        lambda **_: {"hash": "abc", "element_count": 3},
    )
    monkeypatch.setattr(
        "tools.ui_automation.do_list_elements",
        lambda **_: {"elements": many, "count": len(many)},
    )
    monkeypatch.setattr("tools.windows.do_list_windows", lambda: [])
    monkeypatch.setattr(
        "tools.window_scope.resolve_window_scope",
        lambda _t: {"window": None},
    )
    monkeypatch.setattr(
        "tools.screenshot.capture_screenshot",
        lambda **_: {"path": "/tmp/x.png"},
    )

    obs = observe_ui(window_title="Test")
    assert len(obs["tree_sample"]) <= 40
    assert "duration_ms" in obs

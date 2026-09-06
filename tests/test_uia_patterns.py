"""Tests for UIA pattern engine."""
from __future__ import annotations

import pytest

from detection.uia_patterns import (
    apply_pattern_action,
    apply_scroll_pattern,
    read_pattern_state,
    read_control_state,
)


class _FakeToggle:
    def __init__(self, state=0):
        self._state = state
        self.toggled = False

    @property
    def CurrentToggleState(self):
        return self._state

    def Toggle(self):
        self.toggled = True
        self._state = 1 if self._state == 0 else 0


class _FakeScroll:
    def __init__(self):
        self.calls = []

    @property
    def CurrentHorizontallyScrollable(self):
        return True

    @property
    def CurrentVerticallyScrollable(self):
        return True

    @property
    def CurrentHorizontalViewSize(self):
        return 100.0

    @property
    def CurrentVerticalViewSize(self):
        return 25.0

    @property
    def CurrentHorizontalScrollPercent(self):
        return 0.0

    @property
    def CurrentVerticalScrollPercent(self):
        return 50.0

    def Scroll(self, h, v):
        self.calls.append((h, v))

    def SetScrollPercent(self, h, v):
        self.calls.append(("percent", h, v))


def _patch_iface(monkeypatch, mapping):
    def fake_get(raw, pattern):
        if pattern not in mapping:
            raise RuntimeError("no pattern")
        return mapping[pattern]

    monkeypatch.setattr("detection.uia_patterns._has_pattern", lambda _r, p: p in mapping)
    monkeypatch.setattr("detection.uia_patterns._iface", fake_get)


def test_toggle_on_idempotent(monkeypatch):
    toggle = _FakeToggle(state=0)
    _patch_iface(monkeypatch, {"Toggle": toggle})
    result = apply_pattern_action(object(), "Toggle", "on")
    assert result["success"] is True
    assert toggle.toggled is True
    assert toggle.CurrentToggleState == 1

    toggle2 = _FakeToggle(state=1)
    _patch_iface(monkeypatch, {"Toggle": toggle2})
    result2 = apply_pattern_action(object(), "Toggle", "on")
    assert result2["success"] is True
    assert toggle2.toggled is False


def test_scroll_pattern_down(monkeypatch):
    scroll = _FakeScroll()
    _patch_iface(monkeypatch, {"Scroll": scroll})
    result = apply_scroll_pattern(object(), direction="down", amount="large", repeat=2)
    assert result["success"] is True
    assert len(scroll.calls) == 2
    assert scroll.calls[0][1] == 3  # large increment vertical


def test_scroll_set_percent(monkeypatch):
    scroll = _FakeScroll()
    _patch_iface(monkeypatch, {"Scroll": scroll})
    result = apply_scroll_pattern(object(), horizontal_percent=10, vertical_percent=80)
    assert result["success"] is True
    assert scroll.calls[0] == ("percent", 10, 80)


def test_read_toggle_state(monkeypatch):
    toggle = _FakeToggle(state=2)
    _patch_iface(monkeypatch, {"Toggle": toggle})
    monkeypatch.setattr(
        "detection.uia_patterns.list_available_patterns",
        lambda _r: ["Toggle"],
    )
    state = read_control_state(object())
    assert state["patterns"] == ["Toggle"]
    assert state["states"]["Toggle"]["toggle_state"] == "indeterminate"


def test_read_pattern_unavailable(monkeypatch):
    monkeypatch.setattr("detection.uia_patterns._has_pattern", lambda _r, _p: False)
    state = read_pattern_state(object(), "Invoke")
    assert state["available"] is False


def test_invoke_unsupported_pattern(monkeypatch):
    monkeypatch.setattr("detection.uia_patterns._has_pattern", lambda _r, _p: False)
    result = apply_pattern_action(object(), "Invoke", "invoke")
    assert result["success"] is False

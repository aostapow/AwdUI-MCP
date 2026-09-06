"""Tests for list_elements window scope filtering."""
from unittest.mock import patch

from detection.element_model import DetectedElement
from detection.element_scope import (
    element_in_window_scope,
    filter_elements_to_scope,
)


def _scope():
    return {
        "visual": {"x": 100, "y": 200, "w": 400, "h": 600},
        "client": {"x": 110, "y": 250, "w": 380, "h": 550},
        "process_ids": {11196, 9132},
    }


def test_element_in_scope_allows_xaml_pid_mismatch():
    scope = _scope()
    scope["window_title"] = "Calculadora"
    scope["process_ids"] = {1000}
    xaml = DetectedElement(
        name="Borrar",
        role="Button",
        automation_id="clearButton",
        framework_id="XAML",
        x=150,
        y=300,
        width=98,
        height=63,
        process_id=17728,
    )
    with patch("detection.element_coords.to_screen_coords", side_effect=lambda e, _t: e):
        assert element_in_window_scope(xaml, scope) is True


def test_element_in_scope_rejects_non_xaml_foreign_pid():
    scope = _scope()
    foreign = DetectedElement(
        name="Teams",
        role="ListItem",
        automation_id="TeamsItem",
        framework_id="",
        x=150,
        y=300,
        width=200,
        height=32,
        process_id=99999,
    )
    assert element_in_window_scope(foreign, scope) is False


def test_element_in_scope_accepts_calculator_pid_in_client():
    scope = _scope()
    scope["window_title"] = "Calculadora"
    local = DetectedElement(
        name="Borrar",
        role="Button",
        automation_id="clearButton",
        framework_id="XAML",
        x=150,
        y=300,
        width=98,
        height=63,
        process_id=9132,
    )
    with patch("detection.element_coords.to_screen_coords", side_effect=lambda e, _t: e):
        assert element_in_window_scope(local, scope) is True


def test_element_in_scope_rejects_outside_client_rect():
    scope = _scope()
    scope["window_title"] = "Calculadora"
    outside = DetectedElement(
        name="Borrar",
        role="Button",
        automation_id="clearButton",
        framework_id="XAML",
        x=150,
        y=900,
        width=98,
        height=63,
        process_id=9132,
    )
    with patch("detection.element_coords.to_screen_coords", side_effect=lambda e, _t: e):
        assert element_in_window_scope(outside, scope) is False


def test_filter_keeps_left_column_screen_coords():
    """Regression: UIA screen coords with x slightly left of visual rect must not be dropped."""
    scope = {
        "visual": {"x": 122, "y": 397, "w": 531, "h": 843},
        "client": {"x": 107, "y": 318, "w": 407, "h": 666},
        "process_ids": {15032},
        "window_title": "Calculadora",
    }
    elem = DetectedElement(
        name="Uno",
        role="Button",
        automation_id="num1Button",
        framework_id="XAML",
        x=112,
        y=848,
        width=98,
        height=64,
        process_id=15032,
    )

    def fake_region(_title=None):
        return scope["visual"]

    from unittest.mock import patch

    with patch("detection.element_scope.resolve_window_scope", lambda _t=None: scope), patch(
        "detection.element_coords.window_region", fake_region,
    ), patch("detection.element_coords._dpi_scale_for", lambda _t: 1.25):
        assert element_in_window_scope(elem, scope) is True


def test_filter_scope_uwp_screen_coords_integration(monkeypatch):
    """End-to-end scope filter + real to_screen_coords (no mock on coords)."""
    scope = {
        "visual": {"x": 122, "y": 397, "w": 531, "h": 843},
        "client": {"x": 107, "y": 318, "w": 407, "h": 666},
        "process_ids": {15032},
        "window_title": "Calculadora",
    }
    calculator_buttons = [
        ("num1Button", 112, 848, 98, 64),
        ("num5Button", 212, 716, 98, 63),
        ("plusButton", 412, 848, 98, 63),
        ("clearButton", 112, 584, 98, 63),
    ]
    elems = [
        DetectedElement(
            name=aid.replace("Button", ""),
            role="Button",
            automation_id=aid,
            framework_id="XAML",
            x=x,
            y=y,
            width=w,
            height=h,
            process_id=15032,
        )
        for aid, x, y, w, h in calculator_buttons
    ]
    elems.append(
        DetectedElement(
            name="Outside",
            role="Button",
            automation_id="foreign",
            x=0,
            y=0,
            width=40,
            height=40,
            process_id=99999,
        )
    )

    monkeypatch.setattr(
        "detection.element_scope.resolve_window_scope", lambda _t=None: scope,
    )
    monkeypatch.setattr(
        "detection.element_coords.window_region", lambda _t: scope["visual"],
    )
    monkeypatch.setattr("detection.element_coords._dpi_scale_for", lambda _t: 1.25)

    kept, removed, cluster_out, region = filter_elements_to_scope(elems, "Calculadora")

    assert removed == 1
    assert cluster_out == 0
    assert len(kept) == 4
    assert {e.automation_id for e in kept} == {
        "num1Button", "num5Button", "plusButton", "clearButton",
    }


def test_filter_elements_to_scope_counts_removed():
    scope = _scope()
    elems = [
        DetectedElement(
            name="ok", role="Button", automation_id="num1Button",
            x=150, y=300, width=50, height=50, process_id=9132,
        ),
        DetectedElement(
            name="teams", role="ListItem", automation_id="ext",
            x=150, y=300, width=50, height=50, process_id=88888,
        ),
    ]

    def fake_resolve(_title=None):
        return scope

    from unittest.mock import patch

    with patch("detection.element_scope.resolve_window_scope", fake_resolve), patch(
        "detection.element_coords.to_screen_coords", side_effect=lambda e, _t: e,
    ):
        kept, removed, cluster_out, _region = filter_elements_to_scope(elems, "Calculadora")

    assert len(kept) == 1
    assert removed == 1
    assert cluster_out == 0
    assert kept[0].automation_id == "num1Button"

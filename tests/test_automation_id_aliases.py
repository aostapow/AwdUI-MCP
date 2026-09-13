"""Tests for automation_id toggle aliases."""
from __future__ import annotations

from unittest import mock

from detection.automation_id_aliases import alias_candidates


def test_pin_button_aliases():
    assert alias_candidates("NormalAlwaysOnTopButton") == [
        "NormalAlwaysOnTopButton",
        "ExitAlwaysOnTopButton",
    ]
    assert alias_candidates("ExitAlwaysOnTopButton") == [
        "ExitAlwaysOnTopButton",
        "NormalAlwaysOnTopButton",
    ]


def test_find_tries_alias_after_pin():
    from detection.backends.uia_backend import UIABackend
    from detection.element_model import DetectedElement

    backend = UIABackend()
    window = mock.Mock()
    exit_elem = DetectedElement(
        name="Volver a vista completa",
        role="Button",
        automation_id="ExitAlwaysOnTopButton",
        x=100,
        y=10,
        width=80,
        height=30,
    )
    calls: list[str] = []

    def _fake_find(win, aid):
        calls.append(aid)
        if aid == "ExitAlwaysOnTopButton":
            return mock.Mock()
        return None

    with mock.patch(
        "detection.backends.uia_backend._get_desktop",
        return_value=mock.Mock(),
    ), mock.patch(
        "detection.backends.uia_backend._resolve_window",
        return_value=window,
    ), mock.patch(
        "detection.backends.uia_backend._find_raw_by_automation_id",
        side_effect=_fake_find,
    ), mock.patch(
        "detection.backends.uia_backend._pywinauto_to_element",
        return_value=exit_elem,
    ), mock.patch(
        "tools.spy_bridge.spy_available",
        return_value=False,
    ):
        hits = backend.find_elements(
            automation_id="NormalAlwaysOnTopButton",
            window_title="Calculadora",
        )
    assert hits and hits[0].automation_id == "ExitAlwaysOnTopButton"
    assert calls[0] == "NormalAlwaysOnTopButton"
    assert "ExitAlwaysOnTopButton" in calls


def test_orchestrator_accepts_alias_match():
    from detection.element_model import DetectedElement
    from detection.orchestrator import DetectionOrchestrator

    exit_elem = DetectedElement(
        name="Volver a vista completa",
        role="Button",
        automation_id="ExitAlwaysOnTopButton",
        x=100,
        y=10,
        width=80,
        height=30,
    )
    fake_uia = mock.Mock()
    fake_uia.is_available.return_value = True
    fake_uia.find_elements.return_value = [exit_elem]

    orch = DetectionOrchestrator.__new__(DetectionOrchestrator)
    orch._backends = {"uia": fake_uia}
    with mock.patch.object(orch, "_backend_order", return_value=["uia"]), mock.patch(
        "detection.element_scope.filter_dict_elements_to_scope",
        side_effect=lambda elems, wt, **kw: (elems, {"scope_mode": "client_rect"}),
    ):
        result = orch.find_elements(
            automation_id="NormalAlwaysOnTopButton",
            window_title="Calculadora",
        )
    assert result.get("found") is True
    assert result["elements"][0]["automation_id"] == "ExitAlwaysOnTopButton"

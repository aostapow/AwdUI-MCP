"""Tests for strict target scope on find/wait results."""
from unittest.mock import patch

from detection.element_scope import filter_dict_elements_to_scope


def _scope():
    return {
        "window_title": "Calculadora",
        "visual": {"x": 100, "y": 200, "w": 400, "h": 600},
        "client": {"x": 110, "y": 250, "w": 380, "h": 550},
        "process_ids": {1000},
        "allow_renderer_pid": False,
    }


def test_filter_rejects_foreign_element():
    foreign = {
        "name": "Cuadro de búsqueda",
        "role": "Edit",
        "automation_id": "4101",
        "x": 50,
        "y": 50,
        "width": 200,
        "height": 30,
        "process_id": 99999,
    }
    in_scope = {
        "name": "Siete",
        "role": "Button",
        "automation_id": "num7Button",
        "x": 150,
        "y": 300,
        "width": 80,
        "height": 60,
        "process_id": 1000,
        "framework_id": "XAML",
    }
    with patch("detection.element_scope.resolve_window_scope", return_value=_scope()), patch(
        "detection.element_scope.element_in_window_scope",
        side_effect=lambda elem, _scope: elem.get("automation_id") == "num7Button",
    ), patch("tools.framework_detect._get_hwnd_for_window", return_value=12345):
        kept, meta = filter_dict_elements_to_scope(
            [foreign, in_scope],
            "Calculadora",
            automation_id="num7Button",
        )
    assert len(kept) == 1
    assert kept[0]["automation_id"] == "num7Button"
    assert meta["rejected_foreign"] == 1
    assert meta["target_hwnd"] == 12345
    assert meta["scope_mode"] == "client_rect"


def test_orchestrator_find_elements_applies_scope():
    from detection.element_model import DetectedElement
    from detection.orchestrator import DetectionOrchestrator

    orch = DetectionOrchestrator.__new__(DetectionOrchestrator)
    orch._backends = {}
    orch._layered = None

    foreign = DetectedElement(
        name="foreign",
        role="Edit",
        automation_id="num7Button",
        x=10,
        y=10,
        width=50,
        height=20,
        process_id=1,
    )

    class FakeBackend:
        def is_available(self):
            return True

        def find_elements(self, **kwargs):
            return [foreign]

    orch._backends = {"uia": FakeBackend()}
    orch._backend_order = lambda _t=None: ["uia"]
    orch._framework_name = lambda _t=None: "uwp"
    orch._weak_backend_result = lambda *_a, **_k: False

    with patch("detection.element_scope.filter_dict_elements_to_scope", return_value=([], {"scope_mode": "client_rect", "rejected_foreign": 1, "target_hwnd": 99})):
        result = orch.find_elements(automation_id="num7Button", window_title="Calculadora")
    assert result["found"] is False
    assert result["rejected_foreign"] == 1

"""Orchestrator list_elements cache key normalization."""
from __future__ import annotations

from unittest import mock

from detection.orchestrator import (
    DetectionOrchestrator,
    _resolve_list_window_context,
    invalidate_tree_cache,
)


class TestResolveListWindowContext:
    def test_uses_session_target_when_args_empty(self):
        with mock.patch(
            "tools.target_window.get_target",
            return_value="Chat | Teams",
        ), mock.patch(
            "tools.target_window.get_target_hwnd",
            return_value=460854,
        ):
            title, hwnd = _resolve_list_window_context("", 0)
        assert title == "Chat | Teams"
        assert hwnd == 460854

    def test_explicit_args_override_session(self):
        with mock.patch(
            "tools.target_window.get_target",
            return_value="Other",
        ), mock.patch(
            "tools.target_window.get_target_hwnd",
            return_value=1,
        ):
            title, hwnd = _resolve_list_window_context("Explicit", 99)
        assert title == "Explicit"
        assert hwnd == 99


class TestOrchestratorTreeCache:
    def test_second_list_hits_cache_with_session_target(self):
        invalidate_tree_cache()
        orch = DetectionOrchestrator()
        fake_elem = mock.Mock()
        fake_elem.to_dict.return_value = {
            "name": "Chat Awamori",
            "role": "TreeItem",
            "automation_id": "menur1r",
            "x": 185,
            "y": 511,
            "width": 291,
            "height": 33,
        }
        with mock.patch(
            "tools.target_window.get_target",
            return_value="Chat | Teams",
        ), mock.patch(
            "tools.target_window.get_target_hwnd",
            return_value=460854,
        ), mock.patch.object(
            orch._backends["uia"],
            "list_elements",
            return_value=[fake_elem],
        ), mock.patch.object(
            orch,
            "_backend_order",
            return_value=["uia"],
        ), mock.patch.object(
            orch,
            "_framework_name",
            return_value="electron",
        ), mock.patch(
            "detection.element_scope.filter_elements_to_scope",
            return_value=([fake_elem], 0, 0, None),
        ):
            first = orch.list_elements(max_depth=6, role="TreeItem")
            second = orch.list_elements(max_depth=6, role="TreeItem")
        assert first["backend_used"] == "uia"
        assert second["backend_used"] == "cache"
        assert second["count"] == 1


class TestFindElementsBackendOrder:
    def test_automation_id_prefers_uia_before_flaui(self):
        orch = DetectionOrchestrator()
        fake_elem = mock.Mock()
        fake_elem.automation_id = "num7Button"
        fake_elem.to_dict.return_value = {
            "name": "Siete",
            "role": "Button",
            "automation_id": "num7Button",
        }
        call_order: list[str] = []

        def _fake_find(**kwargs):
            call_order.append("uia")
            return [fake_elem]

        uia = orch._backends["uia"]
        flaui = orch._backends.get("flaui")
        with mock.patch.object(
            orch,
            "_backend_order",
            return_value=["flaui", "uia", "msaa"],
        ), mock.patch.object(
            uia,
            "find_elements",
            side_effect=_fake_find,
        ), mock.patch.object(
            flaui,
            "find_elements",
            side_effect=lambda **kwargs: call_order.append("flaui") or [],
        ) if flaui else mock.patch.object(orch, "_backends", orch._backends), mock.patch.object(
            orch,
            "_framework_name",
            return_value="uwp",
        ):
            result = orch.find_elements(
                automation_id="num7Button",
                window_title="Calculadora",
            )
        assert result["found"] is True
        assert call_order == ["uia"]

"""Framework profile registry — per-family policies without product coupling."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from detection.frameworks.registry import (
    framework_auto_depth_map,
    get_profile,
    get_profile_for_window,
    normalize_framework_key,
)
from detection.frameworks.policies import weak_backend_result


def test_normalize_winui_to_uwp():
    assert normalize_framework_key("winui") == "uwp"


def test_uwp_profile_spy_flags():
    p = get_profile("uwp")
    assert p.auto_list_depth == 32
    assert p.prefers_spy_invoke is True
    assert p.prefers_spy_expand_collapse is True
    assert p.expander_dims_via_spy is True
    assert p.backend_order[0] == "flaui"


def test_win32_quick_resolve_spy():
    p = get_profile("win32")
    assert p.quick_resolve_spy_before_find is True
    assert p.auto_list_depth == 12


def test_weak_backend_uwp_flaui_low_aids():
    elements = [MagicMock(automation_id="", role="Pane") for _ in range(3)]
    assert weak_backend_result("uwp", "flaui", elements) is True


def test_weak_backend_win32_msaa_not_uwp_rule():
    elements = [MagicMock(automation_id="", role="Pane")]
    assert weak_backend_result("win32", "msaa", elements) is False


def test_framework_auto_depth_map_includes_winui_alias():
    depths = framework_auto_depth_map()
    assert depths["uwp"] == depths["winui"]


def test_get_profile_for_window():
    with patch("tools.framework_detect.do_detect_framework") as mock_fw:
        mock_fw.return_value = {"framework": "winforms"}
        p = get_profile_for_window("AST")
    assert p.key == "winforms"
    assert "flaui" in p.backend_order


def test_orchestrator_backend_order_uses_profile():
    from detection.orchestrator import DetectionOrchestrator

    orch = DetectionOrchestrator()
    with patch(
        "detection.frameworks.registry.get_profile_for_window",
    ) as mock_gp:
        mock_gp.return_value = get_profile("java_swing")
        order = orch._backend_order("x")
    assert order[0] == "jab" or order == []

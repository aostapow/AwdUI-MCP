"""Stale Calculator instance detection via spy_verify_live pre-flight."""
from __future__ import annotations

from unittest.mock import patch

from tools.spy_bridge import spy_verify_live
from tools.ui_automation import do_invoke_element


def test_spy_verify_live_disabled():
    with patch("tools.spy_bridge.spy_inspect_element") as mock_inspect:
        mock_inspect.return_value = {
            "found": True,
            "properties": {"is_enabled": False, "process_id": 999},
        }
        live = spy_verify_live("clearButton", window_title="Calculadora")
    assert live["live"] is False
    assert live["code"] == "stale_instance"
    assert live["reason"] == "disabled"


def test_invoke_element_returns_stale_instance_when_disabled():
    with patch("tools.spy_bridge.spy_available", return_value=True), patch(
        "tools.spy_bridge.spy_verify_live",
    ) as mock_verify, patch("tools.spy_bridge.spy_invoke_element") as mock_invoke:
        mock_verify.return_value = {
            "live": False,
            "code": "stale_instance",
            "reason": "disabled",
        }
        result = do_invoke_element(
            automation_id="clearButton", window_title="Calculadora",
        )
    assert result["success"] is False
    assert result["code"] == "stale_instance"
    mock_invoke.assert_not_called()


def test_stale_probe_skipped_for_electron():
    from tools.ui_automation import _stale_instance_probe

    with patch(
        "detection.backends.uia_backend._prefer_uia_find_before_spy",
        return_value=True,
    ), patch("tools.spy_bridge.spy_verify_live") as mock_verify:
        assert _stale_instance_probe("menur1oc", "Teams") is None
    mock_verify.assert_not_called()


def test_stale_probe_ignored_when_spy_not_found():
    from tools.ui_automation import _stale_instance_probe

    with patch("tools.spy_bridge.spy_available", return_value=True), patch(
        "tools.spy_bridge.spy_verify_live",
        return_value={"live": False, "reason": "not_found", "code": "stale_instance"},
    ), patch("detection.orchestrator.invalidate_tree_cache") as inv:
        assert _stale_instance_probe("SettingsItem", "Calculadora") is None
    inv.assert_not_called()


def test_launch_app_invalidates_tree_cache():
    from detection.orchestrator import _tree_cache, invalidate_tree_cache

    _tree_cache.clear()
    _tree_cache["Calculadora|uia|5|"] = (0.0, [])
    assert len(_tree_cache) == 1
    n = invalidate_tree_cache()
    assert n == 1
    assert len(_tree_cache) == 0

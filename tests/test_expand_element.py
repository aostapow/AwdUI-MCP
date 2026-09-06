"""Tests for expand_element MCP tool and ExpandCollapse invoke chain."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from tools.spy_bridge import spy_expand_collapse_element


def test_spy_expand_collapse_calls_sidecar():
    with patch("tools.spy_bridge._call") as mock_call:
        mock_call.return_value = {"success": True, "method": "ExpandCollapse.Expand"}
        result = spy_expand_collapse_element(
            automation_id="Units1", window_title="Calculadora", action="expand",
        )
    assert result["success"] is True
    mock_call.assert_called_once_with(
        "expand_collapse",
        {
            "name": "",
            "automation_id": "Units1",
            "window_title": "Calculadora",
            "action": "expand",
        },
    )


def test_do_expand_element_uwp_uses_spy_first():
    from tools.ui_automation import do_expand_element

    with patch("tools.framework_detect.do_detect_framework") as mock_fw, patch(
        "tools.spy_bridge.spy_available", return_value=True,
    ), patch("tools.spy_bridge.spy_expand_collapse_element") as mock_spy:
        mock_fw.return_value = {"framework": "uwp"}
        mock_spy.return_value = {"success": True, "method": "ExpandCollapse.Expand"}
        result = do_expand_element(automation_id="DateCalculationOption", window_title="Calculadora")
    assert result["success"] is True
    assert result["method"] == "ExpandCollapse.Expand"
    assert "elapsed_ms" in result


def test_uia_invoke_chain_includes_expand_collapse():
    from detection.backends.uia_backend import UIABackend
    from detection.element_model import DetectedElement

    backend = UIABackend()
    mock_pattern = MagicMock()
    mock_raw = MagicMock()
    mock_raw.element_info.element = object()

    with patch.object(backend, "_resolve_raw_element", return_value=(mock_raw, None)), patch(
        "pywinauto.uia_defines.get_elem_interface",
    ) as mock_get:
        def _iface(_elem, name):
            if name == "Invoke":
                raise RuntimeError("no invoke")
            if name == "Toggle":
                raise RuntimeError("no toggle")
            if name == "SelectionItem":
                raise RuntimeError("no selection")
            if name == "ExpandCollapse":
                return mock_pattern
            raise RuntimeError(name)

        mock_get.side_effect = _iface
        result = backend.invoke_element(
            DetectedElement(name="Modo", automation_id="Units1", role="ComboBox"),
            window_title="Calculadora",
        )

    assert result["success"] is True
    assert result["method"] == "ExpandCollapse.Expand"
    mock_pattern.Expand.assert_called_once()


def test_expander_header_click_coords_upper_sixth():
    from detection.element_coords import expander_header_click_coords

    elem = {"x": 100, "y": 200, "width": 300, "height": 120}
    cx, cy = expander_header_click_coords(elem)
    assert cx == 250
    assert cy == 220  # 200 + 120//6


def test_do_expand_element_fallback_fast_path_skips_expand_chain():
    from tools.ui_automation import do_expand_element

    expander = {
        "name": "Tema de la aplicación",
        "role": "Group",
        "automation_id": "AppThemeExpander",
        "class_name": "SettingsExpander",
        "x": 110,
        "y": 378,
        "width": 278,
        "height": 85,
    }
    with patch(
        "tools.ui_automation._quick_resolve_element", return_value=expander,
    ), patch("tools.spy_bridge.spy_expand_collapse_element") as mock_spy, patch(
        "tools.ui_automation.do_click", return_value={},
    ), patch("tools.target_window.ensure_focus"):
        result = do_expand_element(
            automation_id="AppThemeExpander",
            window_title="Calculadora",
            fallback_click=True,
        )

    assert result["success"] is True
    assert result["method"] == "HeaderClick"
    assert result.get("fast_path") is True
    assert result["elapsed_ms"] < 2000
    mock_spy.assert_not_called()


def test_do_expand_element_fallback_click_settings_expander():
    from tools.ui_automation import do_expand_element

    expander = {
        "name": "Tema de la aplicación",
        "role": "Group",
        "automation_id": "AppThemeExpander",
        "class_name": "SettingsExpander",
        "x": 259,
        "y": 860,
        "width": 347,
        "height": 112,
    }
    with patch(
        "tools.ui_automation._quick_resolve_element", return_value=expander,
    ), patch("tools.spy_bridge.spy_expand_collapse_element") as mock_spy, patch(
        "tools.ui_automation.do_click", return_value={},
    ), patch("tools.target_window.ensure_focus"), patch(
        "tools.highlight.element_screen_bbox", return_value=None,
    ):
        result = do_expand_element(
            automation_id="AppThemeExpander",
            window_title="Calculadora",
            fallback_click=True,
        )

    assert result["success"] is True
    assert result["method"] == "HeaderClick"
    assert result["used_fallback_click"] is True
    assert result.get("fast_path") is True
    mock_spy.assert_not_called()


def test_expand_element_fallback_uses_screen_bbox_when_no_dimensions():
    from tools.ui_automation import _expand_element_fallback_header_click

    expander = {
        "automation_id": "AppThemeExpander",
        "x": 10,
        "y": 20,
    }
    with patch("tools.highlight.element_screen_bbox", return_value=(500, 600, 200, 90)), patch(
        "tools.ui_automation.do_click",
    ) as mock_click, patch("tools.target_window.ensure_focus"):
        _expand_element_fallback_header_click(expander, "Calculadora")
    cx, cy = mock_click.call_args[0]
    assert cx == 600
    assert cy == 615


def test_expand_element_fallback_prefers_elem_bbox_over_list_walk():
    from tools.ui_automation import _expand_element_fallback_header_click

    expander = {
        "automation_id": "AppThemeExpander",
        "x": 10,
        "y": 20,
        "width": 100,
        "height": 60,
    }
    with patch("tools.highlight.element_screen_bbox") as mock_bbox, patch(
        "detection.element_coords.to_screen_coords", side_effect=lambda e, _t: e,
    ), patch(
        "tools.ui_automation.do_click",
    ) as mock_click, patch("tools.target_window.ensure_focus"):
        _expand_element_fallback_header_click(expander, "Calculadora")
    mock_bbox.assert_not_called()
    cx, cy = mock_click.call_args[0]
    assert cy == 20 + 60 // 6


def test_do_expand_element_no_fallback_hint():
    from tools.ui_automation import do_expand_element

    expander = {
        "name": "Tema",
        "role": "Group",
        "automation_id": "AppThemeExpander",
        "x": 10,
        "y": 20,
        "width": 100,
        "height": 50,
    }
    with patch("tools.framework_detect.do_detect_framework") as mock_fw, patch(
        "tools.spy_bridge.spy_available", return_value=True,
    ), patch("tools.spy_bridge.spy_expand_collapse_element") as mock_spy, patch(
        "tools.ui_automation.do_find_element",
        return_value={"found": True, "elements": [expander]},
    ), patch(
        "detection.backends.uia_backend.get_uia_backend",
    ) as mock_backend:
        mock_fw.return_value = {"framework": "uwp"}
        mock_spy.return_value = {"success": False, "error": "ExpandCollapse not supported"}
        mock_backend.return_value.expand_collapse_element.return_value = {
            "success": False,
        }
        result = do_expand_element(
            automation_id="AppThemeExpander",
            window_title="Calculadora",
            fallback_click=False,
        )

    assert result["success"] is False
    assert result.get("code") == "no_expand_pattern"
    assert "fallback_click=true" in (result.get("hint") or "")

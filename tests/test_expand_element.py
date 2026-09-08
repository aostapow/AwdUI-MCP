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


def test_expander_contains_roles_single_list_pass():
    from tools.ui_automation import _expander_contains_roles

    parent = {
        "automation_id": "AppThemeExpander",
        "x": 100,
        "y": 200,
        "width": 300,
        "height": 100,
    }
    radios = [
        {"role": "RadioButton", "automation_id": "DarkThemeRadioButton", "x": 120, "y": 280, "width": 80, "height": 30},
        {"role": "Text", "name": "label", "x": 120, "y": 210, "width": 80, "height": 20},
    ]
    with patch("tools.ui_automation.do_find_element", return_value={"found": True, "elements": [parent]}), patch(
        "tools.ui_automation.do_list_elements", return_value={"elements": radios},
    ) as list_mock:
        assert _expander_contains_roles(parent, "Calculadora", ("RadioButton", "ListItem")) is True
    list_mock.assert_called_once()
    assert list_mock.call_args.kwargs.get("role") == "RadioButton"


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
    collapsed = dict(expander)
    expanded = dict(expander, height=249)
    refresh_calls = {"n": 0}

    def refresh_mock(_aid, _wt=None):
        refresh_calls["n"] += 1
        return collapsed if refresh_calls["n"] == 1 else expanded

    with patch(
        "tools.ui_automation._quick_resolve_element", return_value=expander,
    ), patch(
        "tools.ui_automation._try_expand_via_interactive_child",
    ) as mock_child, patch(
        "tools.ui_automation._refresh_expander_dims", side_effect=refresh_mock,
    ), patch("tools.spy_bridge.spy_expand_collapse_element") as mock_spy, patch(
        "tools.ui_automation.do_click", return_value={},
    ), patch("tools.target_window.ensure_focus"), patch(
        "tools.wait_tools.do_wait_for_input_idle", return_value={"success": True},
    ):
        result = do_expand_element(
            automation_id="AppThemeExpander",
            window_title="Calculadora",
            fallback_click=True,
        )

    assert result["success"] is True
    assert result["method"] == "ChevronClick"
    assert result.get("fast_path") is True
    assert result["elapsed_ms"] < 4000
    mock_spy.assert_not_called()
    mock_child.assert_not_called()


def test_quick_resolve_uses_control_lookup_before_spy():
    from tools.ui_automation import _quick_resolve_element

    data = {"automation_id": "AppThemeExpander", "role": "Group", "name": "Tema"}
    with patch("tools.control_items._resolve_control", return_value=(object(), None, data, {})), patch(
        "tools.spy_bridge.spy_inspect_element",
    ) as spy_inspect:
        got = _quick_resolve_element(
            automation_id="AppThemeExpander", window_title="Calculadora",
        )
    assert got == data
    spy_inspect.assert_not_called()


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
    collapsed = dict(expander)
    expanded = dict(expander, height=249)
    refresh_calls = {"n": 0}

    def refresh_mock(_aid, _wt=None):
        refresh_calls["n"] += 1
        return collapsed if refresh_calls["n"] == 1 else expanded

    with patch(
        "tools.ui_automation._quick_resolve_element", return_value=expander,
    ), patch(
        "tools.ui_automation._try_expand_via_interactive_child",
    ) as mock_child, patch(
        "tools.ui_automation._refresh_expander_dims", side_effect=refresh_mock,
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
    assert result["method"] == "ChevronClick"
    assert result["used_fallback_click"] is True
    assert result.get("fast_path") is True
    mock_spy.assert_not_called()
    mock_child.assert_not_called()


def test_expander_shell_looks_open_height_heuristic():
    from tools.ui_automation import _expander_shell_looks_open

    assert _expander_shell_looks_open({"height": 249}) is True
    assert _expander_shell_looks_open({"height": 85}) is False


def test_do_expand_element_fallback_already_expanded_skips_click():
    from tools.ui_automation import do_expand_element

    expander = {
        "name": "Tema de la aplicación",
        "role": "Group",
        "automation_id": "AppThemeExpander",
        "class_name": "SettingsExpander",
        "x": 110,
        "y": 378,
        "width": 278,
        "height": 249,
    }

    with patch(
        "tools.ui_automation._quick_resolve_element", return_value=expander,
    ), patch(
        "tools.ui_automation._refresh_expander_dims", return_value=expander,
    ), patch("tools.ui_automation.do_click") as mock_click, patch(
        "tools.wait_tools.do_wait_for_input_idle", return_value={"success": True},
    ):
        result = do_expand_element(
            automation_id="AppThemeExpander",
            window_title="Calculadora",
            fallback_click=True,
        )

    assert result["success"] is True
    assert result["method"] == "AlreadyExpanded"
    assert result.get("fast_path") is True
    mock_click.assert_not_called()


def test_expand_element_fallback_uses_screen_bbox_when_no_dimensions():
    from tools.ui_automation import _expand_element_fallback_header_click

    expander = {
        "automation_id": "AppThemeExpander",
        "x": 10,
        "y": 20,
    }
    with patch("tools.highlight.element_screen_bbox", return_value=(500, 600, 200, 90)), patch(
        "tools.ui_automation._refresh_expander_dims",
        return_value={"automation_id": "AppThemeExpander", "height": 249},
    ), patch(
        "tools.ui_automation.do_click",
    ) as mock_click, patch("tools.target_window.ensure_focus"):
        _expand_element_fallback_header_click(expander, "Calculadora")
    cx, cy = mock_click.call_args[0]
    assert cx == 684
    assert cy == 645


def test_expand_element_fallback_prefers_elem_bbox_over_list_walk():
    from tools.ui_automation import _expand_element_fallback_header_click

    expander = {
        "automation_id": "AppThemeExpander",
        "x": 10,
        "y": 20,
        "width": 100,
        "height": 60,
    }
    with patch("tools.highlight.element_screen_bbox", return_value=None), patch(
        "tools.ui_automation._refresh_expander_dims",
        return_value={"automation_id": "AppThemeExpander", "height": 249},
    ), patch(
        "tools.ui_automation.do_click",
    ) as mock_click, patch("tools.target_window.ensure_focus"):
        _expand_element_fallback_header_click(expander, "Calculadora")
    cx, cy = mock_click.call_args[0]
    assert cx == 94
    assert cy == 50


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

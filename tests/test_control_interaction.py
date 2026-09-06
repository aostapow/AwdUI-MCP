"""Tests for control interaction discovery."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"))

from detection.control_interaction import discover_from_element, format_discovery_report


def _strategy_ids(report: dict) -> list[str]:
    return [s["id"] for s in report["strategies"]]


class TestControlInteractionDiscovery:
    def test_datetimepicker_pane_recommends_type_text(self):
        element = {
            "automation_id": "dtpFecha",
            "name": "jueves, 09/07/2026",
            "role": "Pane",
            "class_name": "WindowsForms10.SysDateTimePick32.app.0.329445b_r8_ad1",
            "patterns": ["LegacyIAccessible"],
        }
        children = [
            {
                "automation_id": "",
                "role": "ComboBox",
                "class_name": "WindowsForms10.COMBOBOX.app.0.329445b_r8_ad1",
                "name": "09/07/2026",
                "patterns": ["Value", "ExpandCollapse"],
                "_states": {
                    "Value": {"available": True, "is_read_only": False, "value": "09/07/2026"},
                },
            }
        ]
        report = discover_from_element(element, children=children)
        assert report["recommended"]["id"] in (
            "explore_children_first",
            "datetime_type",
            "child_value_set",
            "child_combo_type_filter",
        )
        text = format_discovery_report(report)
        assert "type_text" in text or "set_element_value" in text
        assert report["interactive_children"]
        assert report["read"]

    def test_combo_recommends_list_select(self):
        element = {
            "automation_id": "cboGrupo",
            "name": "Grupo:",
            "role": "ComboBox",
            "class_name": "Windows.Forms.ComboBox",
            "patterns": ["ExpandCollapse", "Value"],
        }
        report = discover_from_element(
            element,
            pattern_states={
                "Value": {"available": True, "is_read_only": True, "value": ""},
            },
        )
        ids = _strategy_ids(report)
        assert "combo_list_select" in ids
        assert "click_fallback" in ids
        assert report["recommended"]["id"] == "combo_list_select"

    def test_edit_recommends_set(self):
        element = {
            "automation_id": "teFind",
            "role": "Edit",
            "class_name": "Windows.Forms.TextBox",
            "patterns": ["Value"],
        }
        report = discover_from_element(
            element,
            pattern_states={
                "Value": {"available": True, "is_read_only": False, "value": ""},
            },
        )
        assert report["recommended"]["tools"][0] == "set_element_value"
        assert "edit_type_fallback" in _strategy_ids(report)
        assert "click_fallback" in _strategy_ids(report)

    def test_button_invoke_and_click_fallback(self):
        element = {
            "automation_id": "btnSave",
            "role": "Button",
            "patterns": ["Invoke"],
        }
        report = discover_from_element(element)
        ids = _strategy_ids(report)
        assert report["recommended"]["id"] == "button_invoke"
        assert "click_fallback" in ids
        assert "invoke_element" in report["recommended"]["tools"]

    def test_button_without_invoke_gets_click_fallback(self):
        element = {
            "automation_id": "btnLegacy",
            "role": "Button",
            "patterns": [],
        }
        report = discover_from_element(element)
        ids = _strategy_ids(report)
        assert "click_fallback" in ids
        assert "expander_header_fallback" in ids

    def test_button_with_access_key(self):
        element = {
            "automation_id": "btnOk",
            "role": "Button",
            "patterns": ["Invoke"],
            "access_key": "Alt+o",
        }
        report = discover_from_element(element)
        assert "access_key" in _strategy_ids(report)
        assert report["element"]["access_key"] == "Alt+o"

    def test_checkbox_toggle_and_fallback(self):
        element = {"automation_id": "chkActive", "role": "CheckBox", "patterns": ["Toggle"]}
        report = discover_from_element(element)
        assert report["recommended"]["id"] == "toggle_invoke"
        assert "click_fallback" in _strategy_ids(report)

    def test_radio_selection_and_fallback(self):
        element = {"automation_id": "rbOpt1", "role": "RadioButton", "patterns": ["SelectionItem"]}
        report = discover_from_element(element)
        assert report["recommended"]["id"] == "selection_item"
        assert "click_fallback" in _strategy_ids(report)

    def test_table_grid_strategies(self):
        element = {
            "automation_id": "gcGrid",
            "role": "Table",
            "patterns": ["Grid", "Table", "Scroll"],
        }
        report = discover_from_element(element)
        ids = _strategy_ids(report)
        assert "grid_row_select" in ids
        assert "scroll_container" in ids
        assert report["read"]

    def test_dataitem_read_first(self):
        element = {
            "automation_id": "",
            "role": "DataItem",
            "name": "titulo row 0",
            "patterns": ["SelectionItem", "GridItem"],
        }
        report = discover_from_element(element)
        ids = _strategy_ids(report)
        assert "dataitem_read_first" in ids
        assert "selection_item" in ids

    def test_custom_visual_fallback(self):
        element = {"automation_id": "custom1", "role": "Custom", "patterns": []}
        report = discover_from_element(element)
        ids = _strategy_ids(report)
        assert "visual_fallback" in ids or "explore_children_first" in ids

    def test_tree_item_expand_and_select(self):
        element = {
            "automation_id": "node1",
            "role": "TreeItem",
            "patterns": ["ExpandCollapse", "SelectionItem"],
        }
        report = discover_from_element(element)
        ids = _strategy_ids(report)
        assert "tree_expand" in ids
        assert "selection_item" in ids

    def test_menu_item_invoke_expand_toggle(self):
        element = {
            "automation_id": "mnuFile",
            "role": "MenuItem",
            "patterns": ["Invoke", "ExpandCollapse"],
        }
        report = discover_from_element(element)
        ids = _strategy_ids(report)
        assert "menu_invoke" in ids
        assert "menu_expand_sub" in ids

    def test_split_button(self):
        element = {"automation_id": "split1", "role": "SplitButton", "patterns": ["Invoke", "ExpandCollapse"]}
        report = discover_from_element(element)
        assert report["recommended"]["id"] == "split_button"

    def test_slider_range(self):
        element = {"automation_id": "slider1", "role": "Slider", "patterns": ["RangeValue"]}
        report = discover_from_element(element)
        assert report["recommended"]["id"] == "range_value"
        assert "set_element_value" in report["recommended"]["tools"]

    def test_static_text_read_only(self):
        element = {"automation_id": "lblName", "role": "Text", "patterns": []}
        report = discover_from_element(element)
        assert report["recommended"]["phase"] == "read"
        assert "static_text_read" in _strategy_ids(report)

"""QTP/UFT-style Swf* semantic layer for .NET WinForms controls."""
from __future__ import annotations

from typing import Any, Optional

# UIA role / WinForms class_name → Swf test object class
ROLE_TO_SWF: dict[str, str] = {
    "Window": "SwfWindow",
    "Dialog": "SwfWindow",
    "Button": "SwfButton",
    "Edit": "SwfEdit",
    "Document": "SwfEditor",
    "CheckBox": "SwfCheckBox",
    "RadioButton": "SwfRadioButton",
    "ComboBox": "SwfComboBox",
    "List": "SwfList",
    "ListItem": "SwfListItem",
    "ListView": "SwfListView",
    "Tree": "SwfTreeView",
    "TreeItem": "SwfTreeItem",
    "Tab": "SwfTab",
    "TabItem": "SwfPage",
    "MenuBar": "SwfMenu",
    "MenuItem": "SwfMenuItem",
    "ToolBar": "SwfToolBar",
    "StatusBar": "SwfStatusBar",
    "Label": "SwfLabel",
    "Text": "SwfLabel",
    "Calendar": "SwfCalendar",
    "DataGrid": "SwfTable",
    "Table": "SwfTable",
    "Pane": "SwfObject",
    "Group": "SwfObject",
    "Custom": "SwfObject",
}

CLASS_NAME_HINTS: list[tuple[str, str]] = [
    ("System.Windows.Forms.Button", "SwfButton"),
    ("System.Windows.Forms.TextBox", "SwfEdit"),
    ("System.Windows.Forms.ComboBox", "SwfComboBox"),
    ("System.Windows.Forms.CheckBox", "SwfCheckBox"),
    ("System.Windows.Forms.RadioButton", "SwfRadioButton"),
    ("System.Windows.Forms.ListBox", "SwfList"),
    ("System.Windows.Forms.ListView", "SwfListView"),
    ("System.Windows.Forms.TreeView", "SwfTreeView"),
    ("System.Windows.Forms.TabControl", "SwfTab"),
    ("System.Windows.Forms.TabPage", "SwfPage"),
    ("System.Windows.Forms.Form", "SwfWindow"),
    ("System.Windows.Forms.Label", "SwfLabel"),
    ("System.Windows.Forms.DateTimePicker", "SwfCalendar"),
    ("System.Windows.Forms.DataGridView", "SwfTable"),
    ("System.Windows.Forms.PropertyGrid", "SwfPropertyGrid"),
    ("System.Windows.Forms.ToolStrip", "SwfToolBar"),
    ("System.Windows.Forms.StatusStrip", "SwfStatusBar"),
]

# Per-class identification profiles (QTP Object Identification style)
SWF_PROFILES: dict[str, dict[str, Any]] = {
    "SwfWindow": {
        "mandatory": ["name"],
        "assistive": ["class_name", "automation_id"],
        "smart": ["title_pattern"],
        "ordinal": "index",
        "methods": ["Click", "DblClick", "Highlight", "GetROProperty"],
    },
    "SwfButton": {
        "mandatory": ["automation_id"],
        "assistive": ["name", "role"],
        "smart": ["name", "class_name", "text"],
        "ordinal": "index",
        "methods": ["Click", "DblClick", "FireEvent", "Highlight", "GetROProperty", "Type"],
    },
    "SwfEdit": {
        "mandatory": ["automation_id"],
        "assistive": ["name", "role"],
        "smart": ["name", "class_name"],
        "ordinal": "index",
        "methods": ["Set", "SetSecure", "Type", "SetSelection", "Highlight", "GetROProperty", "GetVisibleText"],
    },
    "SwfEditor": {
        "mandatory": ["automation_id"],
        "assistive": ["name", "role"],
        "smart": ["name", "class_name"],
        "ordinal": "index",
        "methods": ["Set", "Type", "Highlight", "GetROProperty", "GetVisibleText"],
    },
    "SwfComboBox": {
        "mandatory": ["automation_id"],
        "assistive": ["name", "role"],
        "smart": ["name", "class_name"],
        "ordinal": "index",
        "methods": ["Select", "Set", "Click", "Highlight", "GetROProperty"],
    },
    "SwfList": {
        "mandatory": ["automation_id"],
        "assistive": ["name", "role"],
        "smart": ["name", "class_name"],
        "ordinal": "index",
        "methods": ["Select", "Deselect", "GetItem", "Highlight", "GetROProperty"],
    },
    "SwfCheckBox": {
        "mandatory": ["automation_id"],
        "assistive": ["name", "role"],
        "smart": ["name"],
        "ordinal": "index",
        "methods": ["Click", "Set", "Highlight", "GetROProperty"],
    },
    "SwfRadioButton": {
        "mandatory": ["automation_id"],
        "assistive": ["name", "role"],
        "smart": ["name"],
        "ordinal": "index",
        "methods": ["Click", "Select", "Highlight", "GetROProperty"],
    },
    "SwfTab": {
        "mandatory": ["automation_id"],
        "assistive": ["name", "role"],
        "smart": ["name"],
        "ordinal": "index",
        "methods": ["Select", "Highlight", "GetROProperty"],
    },
    "SwfPage": {
        "mandatory": ["name"],
        "assistive": ["automation_id", "role"],
        "smart": ["class_name"],
        "ordinal": "index",
        "methods": ["Select", "Highlight", "GetROProperty"],
    },
    "SwfListView": {
        "mandatory": ["automation_id"],
        "assistive": ["name", "role"],
        "smart": ["name"],
        "ordinal": "index",
        "methods": ["Select", "Click", "Highlight", "GetROProperty"],
    },
    "SwfTreeView": {
        "mandatory": ["automation_id"],
        "assistive": ["name", "role"],
        "smart": ["name"],
        "ordinal": "index",
        "methods": ["Select", "Expand", "Collapse", "Highlight", "GetROProperty"],
    },
    "SwfLabel": {
        "mandatory": ["name"],
        "assistive": ["automation_id", "role"],
        "smart": ["class_name"],
        "ordinal": "index",
        "methods": ["Highlight", "GetROProperty", "GetVisibleText"],
    },
    "SwfObject": {
        "mandatory": ["automation_id"],
        "assistive": ["name", "role", "class_name"],
        "smart": ["name", "class_name"],
        "ordinal": "index",
        "methods": ["Click", "Highlight", "GetROProperty", "GetVisibleText"],
    },
}

SWF_TO_ROLE: dict[str, str] = {
    "SwfWindow": "Window",
    "SwfButton": "Button",
    "SwfEdit": "Edit",
    "SwfEditor": "Document",
    "SwfComboBox": "ComboBox",
    "SwfList": "List",
    "SwfCheckBox": "CheckBox",
    "SwfRadioButton": "RadioButton",
    "SwfTab": "Tab",
    "SwfPage": "TabItem",
    "SwfListView": "List",
    "SwfTreeView": "Tree",
    "SwfLabel": "Text",
    "SwfMenu": "MenuBar",
    "SwfMenuItem": "MenuItem",
    "SwfCalendar": "Calendar",
    "SwfTable": "Table",
    "SwfToolBar": "ToolBar",
    "SwfStatusBar": "StatusBar",
    "SwfPropertyGrid": "Pane",
    "SwfObject": "",
}


def infer_swf_class(
    role: str = "",
    class_name: str = "",
    obj_class: str = "",
) -> str:
    if obj_class and obj_class.startswith("Swf"):
        return obj_class
    cn = class_name or ""
    for hint, swf in CLASS_NAME_HINTS:
        if hint.lower() in cn.lower():
            return swf
    return ROLE_TO_SWF.get(role, "SwfObject")


def role_for_swf(swf_class: str) -> Optional[str]:
    role = SWF_TO_ROLE.get(swf_class, "")
    return role or None


def profile_for(swf_class: str) -> dict[str, Any]:
    return SWF_PROFILES.get(swf_class, SWF_PROFILES["SwfObject"])


def allowed_methods(swf_class: str) -> list[str]:
    return list(profile_for(swf_class).get("methods", ["Click", "Highlight"]))


def _prop_value(elem: dict, prop: str) -> str:
    if prop == "text":
        return elem.get("name", "") or elem.get("value", "")
    if prop == "title_pattern":
        return elem.get("name", "")
    val = elem.get(prop, "")
    return str(val) if val is not None else ""


def build_identification(elem: dict, swf_class: str) -> dict[str, dict[str, str]]:
    """Build mandatory / assistive / smart property sets from an element."""
    prof = profile_for(swf_class)
    ident: dict[str, dict[str, str]] = {"mandatory": {}, "assistive": {}, "smart": {}}
    for tier in ("mandatory", "assistive", "smart"):
        for prop in prof.get(tier, []):
            val = _prop_value(elem, prop)
            if val:
                ident[tier][prop] = val
    if not ident["mandatory"].get("role"):
        role = role_for_swf(swf_class) or elem.get("role", "")
        if role:
            ident["assistive"].setdefault("role", role)
    ordinal = prof.get("ordinal")
    if ordinal:
        ident["ordinal"] = {ordinal: str(elem.get("index", 0))}
    return ident


def validate_method(swf_class: str, method: str) -> Optional[str]:
    method = method.strip()
    allowed = allowed_methods(swf_class)
    if method not in allowed:
        return f"Method '{method}' not supported for {swf_class}. Allowed: {', '.join(allowed)}"
    return None

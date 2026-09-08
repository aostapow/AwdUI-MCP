"""Generic UIA control → MCP tool strategy discovery (no app-specific rules)."""
from __future__ import annotations

from typing import Any, Optional

# Roles that are usually containers — map children, do not click the shell.
_CONTAINER_ROLES = frozenset(
    {
        "Pane",
        "Group",
        "Custom",
        "Window",
        "Document",
        "Tab",
        "ToolBar",
        "StatusBar",
        "Menu",
        "MenuBar",
        "Tree",
        "List",
        "Table",
        "DataGrid",
        "AppBar",
        "Separator",
        "ToolTip",
        "TitleBar",
        "ProgressBar",
    }
)

_INTERACTIVE_ROLES = frozenset(
    {
        "Button",
        "ComboBox",
        "Edit",
        "ListItem",
        "MenuItem",
        "CheckBox",
        "RadioButton",
        "Hyperlink",
        "TabItem",
        "TreeItem",
        "DataItem",
        "Spinner",
        "Slider",
        "SplitButton",
        "ScrollBar",
        "Thumb",
        "Calendar",
        "HeaderItem",
        "Image",
        "Text",
    }
)

_READ_ONLY_ROLES = frozenset({"Text", "ToolTip", "ProgressBar", "Image", "Header", "HeaderItem"})


def _patterns(element: dict) -> set[str]:
    raw = element.get("patterns") or []
    return {str(p) for p in raw}


def _value_state(pattern_states: Optional[dict], element: dict) -> dict:
    if pattern_states and "Value" in pattern_states:
        return pattern_states["Value"] or {}
    states = element.get("_states") or {}
    if isinstance(states.get("Value"), dict):
        return states["Value"]
    return {}


def _is_read_only_value(element: dict, pattern_states: Optional[dict]) -> bool:
    vs = _value_state(pattern_states, element)
    if vs.get("available") is False:
        return True
    return bool(vs.get("is_read_only", False))


def _access_key(element: dict) -> str:
    for key in ("access_key", "AccessKey", "accelerator_key", "AcceleratorKey"):
        val = (element.get(key) or "").strip()
        if val:
            return val
    return ""


def _strategy(
    sid: str,
    tools: list[str],
    steps: list[str],
    confidence: str = "high",
    note: str = "",
    phase: str = "act",
) -> dict:
    return {
        "id": sid,
        "tools": tools,
        "steps": steps,
        "confidence": confidence,
        "note": note,
        "phase": phase,
    }


def _score(confidence: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(confidence, 0)


def _datetime_picker_class(class_name: str) -> bool:
    cl = (class_name or "").lower()
    return "sysdatetimepick" in cl or "datetimepicker" in cl


def _interactive_children(children: Optional[list[dict]]) -> list[dict]:
    if not children:
        return []
    out: list[dict] = []
    for child in children:
        role = (child.get("role") or "").strip()
        pats = _patterns(child)
        if role in _INTERACTIVE_ROLES or pats & {
            "Invoke",
            "Value",
            "ExpandCollapse",
            "SelectionItem",
            "Toggle",
            "Text",
        }:
            out.append(
                {
                    "role": role,
                    "automation_id": child.get("automation_id", ""),
                    "name": child.get("name", ""),
                    "patterns": sorted(pats),
                }
            )
    return out


def _append_unique(strategies: list[dict], item: dict) -> None:
    if any(s["id"] == item["id"] for s in strategies):
        return
    strategies.append(item)


def _read_strategies(element: dict, role: str, pats: set[str]) -> list[dict]:
    reads: list[dict] = []
    _append_unique(
        reads,
        _strategy(
            "read_spy_inspect",
            ["spy_inspect", "get_element_properties"],
            ["spy_inspect for patterns and state", "get_element_properties for Value/Text"],
            confidence="high",
            phase="read",
        ),
    )
    if "Value" in pats or role in ("Edit", "ComboBox", "Spinner", "Slider"):
        _append_unique(
            reads,
            _strategy(
                "read_value",
                ["get_element_properties"],
                ["Read Value pattern / LegacyIAccessible value"],
                confidence="high",
                phase="read",
            ),
        )
    if "Toggle" in pats or role == "CheckBox":
        _append_unique(
            reads,
            _strategy(
                "read_toggle",
                ["spy_inspect"],
                ["Check ToggleState in spy_inspect"],
                confidence="high",
                phase="read",
            ),
        )
    if role in ("Table", "DataGrid", "Calendar") or "Grid" in pats:
        _append_unique(
            reads,
            _strategy(
                "read_grid_cells",
                ["list_elements", "spy_inspect"],
                [
                    "list_elements(role='DataItem') — read Value, not only name",
                    "Group actions under grid parent",
                ],
                confidence="high",
                phase="read",
            ),
        )
    if role in _CONTAINER_ROLES and role not in ("Table", "DataGrid", "List", "Tree"):
        _append_unique(
            reads,
            _strategy(
                "read_children",
                ["list_elements"],
                ["list_elements by role for interactive children"],
                confidence="medium",
                phase="read",
            ),
        )
    return reads


def _click_fallback(note: str = "WinForms legacy or Invoke failure") -> dict:
    return _strategy(
        "click_fallback",
        ["click_element", "click"],
        [
            "click_element (Invoke → SelectionItem → Toggle chain)",
            "click(coords) only if UIA activation fails",
        ],
        confidence="medium",
        note=note,
        phase="fallback",
    )


def _access_key_strategy(element: dict) -> Optional[dict]:
    ak = _access_key(element)
    if not ak:
        return None
    return _strategy(
        "access_key",
        ["send_keys"],
        [f"send_keys('{ak}') if control supports accelerator"],
        confidence="low",
        phase="fallback",
    )


def _scroll_strategies(pats: set[str], role: str) -> list[dict]:
    if "Scroll" not in pats and role not in ("List", "Tree", "Table", "DataGrid", "Document"):
        return []
    return [
        _strategy(
            "scroll_container",
            ["scroll", "list_elements"],
            [
                "scroll on container if virtualized",
                "list_elements after scroll for off-screen items",
            ],
            confidence="medium",
            phase="act",
        ),
    ]


def _ocr_fallback(role: str, pats: set[str]) -> Optional[dict]:
    if pats & {"Invoke", "Value", "ExpandCollapse", "SelectionItem", "Toggle", "Text"}:
        return None
    if role in ("Custom", "Image") or not pats:
        return _strategy(
            "visual_fallback",
            ["smart_find", "find_text"],
            ["smart_find cascade", "find_text / template if UIA tree empty"],
            confidence="low",
            phase="fallback",
        )
    return None


def _strategies_button(
    element: dict,
    pats: set[str],
    strategies: list[dict],
) -> None:
    if "Invoke" in pats or not pats:
        _append_unique(
            strategies,
            _strategy(
                "button_invoke",
                ["invoke_element"],
                ["invoke_element(automation_id=…) — InvokePattern"],
                confidence="high" if "Invoke" in pats else "medium",
            ),
        )
    if "Toggle" in pats:
        _append_unique(
            strategies,
            _strategy(
                "button_toggle",
                ["invoke_element"],
                ["invoke_element toggles ToggleState"],
            ),
        )
    if "ExpandCollapse" in pats:
        _append_unique(
            strategies,
            _strategy(
                "button_expand",
                ["expand_element", "invoke_element", "list_elements"],
                [
                    "expand_element for drop-down portion",
                    "list_elements for menu items after expand",
                ],
                confidence="medium",
            ),
        )
    if "SelectionItem" in pats:
        _append_unique(
            strategies,
            _strategy(
                "button_selection",
                ["invoke_element"],
                ["invoke_element — SelectionItem.Select in chain"],
            ),
        )
    _append_unique(strategies, _click_fallback())
    ak = _access_key_strategy(element)
    if ak:
        _append_unique(strategies, ak)
    if not pats:
        _append_unique(
            strategies,
            _strategy(
                "expander_header_fallback",
                ["expand_element"],
                ["expand_element(fallback_click=true) for header-style expanders without pattern"],
                confidence="low",
                note="Chevron visible in tree but no ExpandCollapse pattern",
            ),
        )


def _strategies_combo(
    element: dict,
    pats: set[str],
    pattern_states: Optional[dict],
    strategies: list[dict],
) -> None:
    _append_unique(
        strategies,
        _strategy(
            "combo_list_select",
            ["expand_element", "list_control_items", "select_control_item"],
            [
                "expand_element or invoke ExpandCollapse",
                "list_control_items(automation_id=…) for options",
                "select_control_item(automation_id=…, value=…)",
            ],
        ),
    )
    if "Value" in pats and not _is_read_only_value(element, pattern_states):
        _append_unique(
            strategies,
            _strategy(
                "combo_type_filter",
                ["set_element_value", "click_element", "type_text"],
                [
                    "set_element_value to filter editable combo",
                    "click_element + type_text if Value set fails",
                ],
                confidence="medium",
            ),
        )
    _append_unique(strategies, _click_fallback("Combo without cooperating patterns"))


def _strategies_edit(pats: set[str], pattern_states: Optional[dict], element: dict, strategies: list[dict]) -> None:
    if not _is_read_only_value(element, pattern_states):
        _append_unique(
            strategies,
            _strategy(
                "edit_set",
                ["set_element_value"],
                ["set_element_value(automation_id=…, value=…)"],
            ),
        )
        _append_unique(
            strategies,
            _strategy(
                "edit_type_fallback",
                ["click_element", "type_text"],
                ["click_element to focus", "type_text if Value pattern fails"],
                confidence="medium",
                phase="fallback",
            ),
        )
    if "Text" in pats:
        _append_unique(
            strategies,
            _strategy(
                "document_text",
                ["set_element_value", "clipboard"],
                ["set_element_value for Text pattern", "clipboard paste for rich Document"],
                confidence="medium",
            ),
        )
    _append_unique(strategies, _click_fallback())


def _strategies_checkbox_toggle(pats: set[str], strategies: list[dict]) -> None:
    _append_unique(
        strategies,
        _strategy(
            "toggle_invoke",
            ["invoke_element"],
            ["invoke_element — TogglePattern on/off"],
        ),
    )
    _append_unique(strategies, _click_fallback())


def _strategies_selection_item(strategies: list[dict], note: str = "") -> None:
    _append_unique(
        strategies,
        _strategy(
            "selection_item",
            ["select_control_item", "invoke_element"],
            [
                "select_control_item(automation_id=…, value=…)"
                + (f" ({note})" if note else ""),
                "invoke_element — SelectionItem.Select fallback",
            ],
        ),
    )
    _append_unique(strategies, _click_fallback())


def _strategies_list_combo_container(role: str, pats: set[str], strategies: list[dict]) -> None:
    _append_unique(
        strategies,
        _strategy(
            "list_select_item",
            ["list_control_items", "select_control_item"],
            [
                "list_control_items on List parent",
                "select_control_item(value=…) on target ListItem",
            ],
        ),
    )
    for s in _scroll_strategies(pats, role):
        _append_unique(strategies, s)


def _strategies_grid(role: str, pats: set[str], strategies: list[dict]) -> None:
    _append_unique(
        strategies,
        _strategy(
            "grid_row_select",
            ["list_control_items", "select_control_item", "invoke_element", "click_element"],
            [
                "list_control_items on grid — read Value per cell",
                "select_control_item(value=…); double_click=true for lookup modals",
                "invoke_element on row/cell fallback",
            ],
        ),
    )
    for s in _scroll_strategies(pats, role):
        _append_unique(strategies, s)
    _append_unique(strategies, _click_fallback("Cell without SelectionItem"))


def _strategies_data_item(strategies: list[dict]) -> None:
    _append_unique(
        strategies,
        _strategy(
            "dataitem_read_first",
            ["spy_inspect"],
            ["Always read Value/LegacyIAccessible — name may be 'col row N'"],
            phase="read",
        ),
    )
    _strategies_selection_item(strategies, note="prefer parent grid context")
    _append_unique(strategies, _click_fallback("Avoid orphan cell click when possible"))


def _strategies_tree_item(pats: set[str], strategies: list[dict]) -> None:
    if "ExpandCollapse" in pats:
        _append_unique(
            strategies,
            _strategy(
                "tree_expand",
                ["expand_element", "list_control_items"],
                [
                    "expand_element on TreeItem with children",
                    "list_control_items / list_elements for nested nodes",
                ],
            ),
        )
    if "Invoke" in pats or "SelectionItem" in pats:
        _strategies_selection_item(strategies, note="leaf or selectable node")
    if "Toggle" in pats:
        _append_unique(strategies, _strategy("tree_toggle", ["invoke_element"], ["invoke_element toggle on checkeable tree item"]))
    _append_unique(strategies, _click_fallback())


def _strategies_menu_item(pats: set[str], strategies: list[dict]) -> None:
    if "Invoke" in pats:
        _append_unique(strategies, _strategy("menu_invoke", ["invoke_element"], ["invoke_element executes command"]))
    if "ExpandCollapse" in pats:
        _append_unique(
            strategies,
            _strategy(
                "menu_expand_sub",
                ["expand_element", "list_control_items"],
                ["expand_element opens submenu", "list_control_items or list_elements(MenuItem)"],
                confidence="medium",
            ),
        )
    if "Toggle" in pats:
        _append_unique(strategies, _strategy("menu_toggle", ["invoke_element"], ["invoke_element toggles checked menu item"]))
    if "SelectionItem" in pats:
        _strategies_selection_item(strategies)
    _append_unique(strategies, _click_fallback())


def _strategies_split_button(strategies: list[dict]) -> None:
    _append_unique(
        strategies,
        _strategy(
            "split_button",
            ["invoke_element", "expand_element", "list_elements"],
            [
                "invoke_element on main button area",
                "expand_element on drop-down chevron",
                "list_elements for menu items",
            ],
        ),
    )
    _append_unique(strategies, _click_fallback())


def _strategies_range(role: str, pats: set[str], strategies: list[dict]) -> None:
    tools = ["set_element_value", "send_keys"]
    steps = ["set_element_value if RangeValue/Value supported"]
    if role in ("ScrollBar", "Spinner"):
        steps.append("send_keys arrows/PageUp/PageDown")
    if role == "ScrollBar":
        tools.append("scroll")
        steps.append("scroll or drag Thumb sibling")
    _append_unique(
        strategies,
        _strategy("range_value", tools, steps, confidence="medium"),
    )


def _strategies_thumb(strategies: list[dict]) -> None:
    _append_unique(
        strategies,
        _strategy(
            "thumb_drag",
            ["drag"],
            ["drag Thumb via Transform pattern / coordinate drag"],
            confidence="medium",
        ),
    )


def _strategies_hyperlink(strategies: list[dict]) -> None:
    _append_unique(
        strategies,
        _strategy("hyperlink_invoke", ["invoke_element"], ["invoke_element opens link"]),
    )
    _append_unique(strategies, _click_fallback())


def _strategies_container(
    element: dict,
    role: str,
    class_name: str,
    kids: list[dict],
    strategies: list[dict],
) -> None:
    child_role = {
        "Tab": "TabItem",
        "Tree": "TreeItem",
        "Menu": "MenuItem",
        "MenuBar": "MenuItem",
        "ToolBar": "Button",
    }.get(role, "")
    if child_role:
        _append_unique(
            strategies,
            _strategy(
                "container_list_children",
                ["list_elements"],
                [f"list_elements(role='{child_role}') — act on child, not container shell"],
                confidence="high",
                phase="read",
            ),
        )
    if _datetime_picker_class(class_name):
        _append_unique(
            strategies,
            _strategy(
                "datetime_type",
                ["click_element", "type_text"],
                ["click_element on date pane", "type_text date digits or use child combo"],
                confidence="high",
            ),
        )
    for child in kids:
        child_role = child.get("role", "")
        child_pats = set(child.get("patterns") or [])
        if child_role == "ComboBox" and "Value" in child_pats:
            _append_unique(
                strategies,
                _strategy(
                    "child_combo_type_filter",
                    ["set_element_value", "click_element", "type_text"],
                    [
                        f"set_element_value on child combo id={child.get('automation_id') or '(child)'}",
                        "or click child + type_text",
                    ],
                    confidence="high",
                ),
            )
        if child_role == "Edit" and "Value" in child_pats:
            _append_unique(
                strategies,
                _strategy(
                    "child_value_set",
                    ["set_element_value"],
                    [f"set_element_value on child Edit id={child.get('automation_id') or '(child)'}"],
                    confidence="high",
                ),
            )
    if kids or role in ("Pane", "Group", "Custom"):
        _append_unique(
            strategies,
            _strategy(
                "explore_children_first",
                ["spy_inspect", "list_elements", "discover_control_interaction"],
                [
                    "Inspect interactive children before acting on container",
                    "Re-run discover_control_interaction on child automation_id",
                ],
                confidence="high" if kids else "medium",
            ),
        )


def _strategies_for_element(
    element: dict,
    pattern_states: Optional[dict] = None,
    children: Optional[list[dict]] = None,
) -> tuple[list[dict], dict]:
    role = (element.get("role") or "").strip()
    class_name = element.get("class_name") or ""
    pats = _patterns(element)
    strategies: list[dict] = []
    kids = _interactive_children(children)

    # Read phase (prepended after act sorting — handled at end)
    read_strats = _read_strategies(element, role, pats)

    if role in _READ_ONLY_ROLES:
        if role == "ProgressBar":
            _append_unique(
                strategies,
                _strategy(
                    "progress_read_only",
                    ["get_element_properties", "spy_inspect"],
                    ["Read RangeValue/Value only — do not act"],
                    phase="read",
                ),
            )
        elif role in ("Text", "ToolTip"):
            _append_unique(
                strategies,
                _strategy(
                    "static_text_read",
                    ["spy_inspect", "get_element_properties"],
                    ["Read name/text only"],
                    phase="read",
                ),
            )
        elif role == "Image":
            visual = _ocr_fallback(role, pats)
            if visual:
                _append_unique(strategies, visual)

    elif role == "Button":
        _strategies_button(element, pats, strategies)

    elif role == "SplitButton":
        _strategies_split_button(strategies)

    elif role == "ComboBox":
        _strategies_combo(element, pats, pattern_states, strategies)

    elif role in ("Edit", "Document"):
        _strategies_edit(pats, pattern_states, element, strategies)

    elif role == "CheckBox":
        _strategies_checkbox_toggle(pats, strategies)

    elif role == "RadioButton":
        _strategies_selection_item(strategies, note="radio group — prefer select_control_item")

    elif role == "ListItem":
        if "Invoke" in pats:
            _append_unique(strategies, _strategy("listitem_invoke", ["invoke_element"], ["invoke_element if ListItem behaves as button"]))
        _strategies_selection_item(strategies)
        if "ExpandCollapse" in pats:
            _append_unique(strategies, _strategy("listitem_expand", ["expand_element"], ["expand_element before selecting nested items"]))
        if "Toggle" in pats:
            _append_unique(strategies, _strategy("listitem_toggle", ["invoke_element"], ["invoke_element toggle"]))

    elif role == "List":
        _strategies_list_combo_container(role, pats, strategies)

    elif role in ("Table", "DataGrid", "Calendar"):
        _strategies_grid(role, pats, strategies)

    elif role == "DataItem":
        _strategies_data_item(strategies)

    elif role == "TreeItem":
        _strategies_tree_item(pats, strategies)

    elif role == "MenuItem":
        _strategies_menu_item(pats, strategies)

    elif role == "TabItem":
        _strategies_selection_item(strategies, note="tab switch")

    elif role in ("Slider", "Spinner", "ScrollBar"):
        _strategies_range(role, pats, strategies)

    elif role == "Thumb":
        _strategies_thumb(strategies)

    elif role == "Hyperlink":
        _strategies_hyperlink(strategies)

    elif role in _CONTAINER_ROLES or (role == "Custom" and not strategies):
        _strategies_container(element, role, class_name, kids, strategies)

    # Pattern-based additions when role alone is insufficient
    if role not in ("Button", "CheckBox", "ComboBox", "Edit", "Document"):
        if "Invoke" in pats and not any(s["id"] in ("button_invoke", "menu_invoke", "hyperlink_invoke") for s in strategies):
            _append_unique(
                strategies,
                _strategy(
                    "pattern_invoke",
                    ["invoke_element"],
                    ["invoke_element — Invoke pattern present"],
                    confidence="medium",
                ),
            )
        if "Toggle" in pats and role != "CheckBox":
            _append_unique(strategies, _strategy("pattern_toggle", ["invoke_element"], ["invoke_element — Toggle pattern"]))
        if "ExpandCollapse" in pats and role not in ("TreeItem", "MenuItem", "ComboBox"):
            _append_unique(
                strategies,
                _strategy(
                    "pattern_expand",
                    ["expand_element", "list_elements"],
                    ["expand_element then list children"],
                    confidence="medium",
                ),
            )
        if "SelectionItem" in pats and role not in ("RadioButton", "ListItem", "TabItem", "DataItem"):
            _strategies_selection_item(strategies)

    for s in _scroll_strategies(pats, role):
        _append_unique(strategies, s)

    ak = _access_key_strategy(element)
    if ak and role not in ("Button",):
        _append_unique(strategies, ak)

    visual = _ocr_fallback(role, pats)
    if visual:
        _append_unique(strategies, visual)

    if not strategies:
        _append_unique(
            strategies,
            _strategy(
                "inspect_then_act",
                ["spy_inspect", "invoke_element", "click_element"],
                [
                    "spy_inspect for patterns",
                    "invoke_element if any pattern",
                    "click_element fallback",
                ],
                confidence="low",
            ),
        )

    from detection.uia_control_map import merge_official_strategies

    map_meta = merge_official_strategies(strategies, role, pats)

    # Sort act strategies by confidence; keep read/fallback grouped in output
    act_like = [s for s in strategies if s.get("phase") != "read"]
    read_like = [s for s in strategies if s.get("phase") == "read"]
    act_like.sort(
        key=lambda s: (_score(s.get("confidence", "low")), 0 if s.get("source") == "uia_control_map" else 1),
        reverse=True,
    )
    # Merge catalog read strategies not duplicated
    for rs in read_strats:
        _append_unique(read_like, rs)
    return read_like + act_like, map_meta


def _avoid_list(element: dict, strategies: list[dict]) -> list[str]:
    avoid = ["click coordinates unless UIA patterns exhausted"]
    pats = _patterns(element)
    role = (element.get("role") or "").strip()
    if not pats:
        avoid.append("assuming Invoke without spy_inspect confirmation")
    if any(s["id"] == "combo_list_select" for s in strategies):
        avoid.append("set_element_value on read-only ComboBox before listing items")
    if role == "DataItem":
        avoid.append("acting on orphan DataItem without grid parent context")
    if role in ("Pane", "Group", "Window", "Tab", "Tree", "Table"):
        avoid.append("clicking container shell — target interactive child")
    if role in ("Text", "ToolTip", "ProgressBar"):
        avoid.append("trying to edit read-only static controls")
    return avoid


def discover_from_element(
    element: dict,
    children: Optional[list[dict]] = None,
    pattern_states: Optional[dict] = None,
    repo_hints: str = "",
) -> dict:
    """Build interaction report from UIA element metadata (generic rules only)."""
    strategies, official_map = _strategies_for_element(element, pattern_states, children)
    act_strategies = [s for s in strategies if s.get("phase") not in ("read",)]
    read_strategies = [s for s in strategies if s.get("phase") == "read"]
    role = (element.get("role") or "").strip()
    if role in _READ_ONLY_ROLES and read_strategies:
        recommended = read_strategies[0]
    elif act_strategies:
        recommended = act_strategies[0]
    elif strategies:
        recommended = strategies[0]
    else:
        recommended = _strategy(
            "inspect_then_act",
            ["spy_inspect"],
            ["spy_inspect first"],
            confidence="low",
        )
    kids = _interactive_children(children)
    report: dict[str, Any] = {
        "element": {
            "automation_id": element.get("automation_id", ""),
            "name": element.get("name", ""),
            "role": element.get("role", ""),
            "class_name": element.get("class_name", ""),
            "patterns": sorted(_patterns(element)),
            "access_key": _access_key(element) or None,
        },
        "recommended": recommended,
        "read": read_strategies,
        "strategies": strategies,
        "interactive_children": kids,
        "avoid": _avoid_list(element, strategies),
        "official_map": official_map,
    }
    if (repo_hints or "").strip():
        from detection.hint_consume import apply_hints_to_discovery_report

        report = apply_hints_to_discovery_report(report, repo_hints)
    try:
        from addin_sdk.registry import get_registry

        reg = get_registry()
        if reg:
            for loaded in reg.addins:
                report = loaded.instance.enrich_control_interaction(
                    element, report, loaded.ctx
                )
    except Exception:
        pass
    return report


def format_discovery_report(report: dict) -> str:
    """Human-readable report for MCP tool output."""
    elem = report.get("element") or {}
    lines = [
        "Control interaction discovery (generic UIA):",
        f"  role={elem.get('role', '')} automation_id={elem.get('automation_id', '')}",
        f"  patterns={elem.get('patterns', [])}",
    ]
    omap = report.get("official_map") or {}
    if omap.get("in_map"):
        from detection.uia_control_map import format_map_note

        lines.append(format_map_note(omap))
    if elem.get("access_key"):
        lines.append(f"  access_key={elem.get('access_key')}")
    read = report.get("read") or []
    if read:
        lines.append("Read (before act):")
        for r in read[:4]:
            lines.append(f"  - [{r.get('id')}] {', '.join(r.get('tools') or [])}")
    rec = report.get("recommended") or {}
    lines.append(f"Recommended act [{rec.get('id', '')}] ({rec.get('confidence', '')}):")
    for step in rec.get("steps") or []:
        lines.append(f"  → {step}")
    tools = rec.get("tools") or []
    if tools:
        lines.append(f"  tools: {', '.join(tools)}")
    kids = report.get("interactive_children") or []
    if kids:
        lines.append(f"Interactive children ({len(kids)}):")
        for c in kids[:8]:
            lines.append(
                f"  - {c.get('role')} id={c.get('automation_id', '')} "
                f"patterns={c.get('patterns', [])}"
            )
    alts = [s for s in (report.get("strategies") or []) if s.get("phase") != "read" and s.get("id") != rec.get("id")]
    if alts:
        lines.append("Other act / fallback:")
        for alt in alts[:10]:
            phase = alt.get("phase", "act")
            lines.append(
                f"  - {alt.get('id')} ({phase}): {', '.join(alt.get('tools') or [])}"
            )
    avoid = report.get("avoid") or []
    if avoid:
        lines.append("Avoid:")
        for a in avoid:
            lines.append(f"  - {a}")
    hints = report.get("repo_hints")
    if hints:
        lines.append("Repo agent_hints:")
        for hl in hints.strip().splitlines()[:12]:
            lines.append(f"  {hl}")
    return "\n".join(lines)

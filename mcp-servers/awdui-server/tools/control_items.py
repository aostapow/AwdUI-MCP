"""list_control_items / select_control_item — role-aware item pickers."""
from __future__ import annotations

import sys
from typing import Any, Optional


class _ControlView:
    def __init__(self, data: dict):
        self.role = data.get("role", "")
        self.name = data.get("name", "")
        self.value = data.get("value", "")
        self.automation_id = data.get("automation_id", "")


def _resolve_control(
    automation_id: str,
    window_title: Optional[str] = None,
) -> tuple[Optional[object], Optional[_ControlView], Optional[dict], dict]:
    from tools.window_scope import resolve_window_scope

    scope = resolve_window_scope(window_title)
    title = scope.get("resolved_title") or window_title
    if sys.platform != "win32":
        return None, None, None, scope
    from detection.backends.uia_backend import (
        _find_raw_by_automation_id,
        _find_window,
        _get_desktop,
        _pywinauto_to_element,
    )

    desktop = _get_desktop()
    window = _find_window(desktop, title)
    if not window:
        return None, None, None, scope
    raw = _find_raw_by_automation_id(window, automation_id)
    if not raw:
        return None, None, None, scope
    det = _pywinauto_to_element(raw)
    data = det.to_dict() if det else {"role": "", "name": "", "value": "", "automation_id": automation_id}
    return raw, _ControlView(data), data, scope


def _expand_combo(raw) -> None:
    try:
        from pywinauto.uia_defines import get_elem_interface

        get_elem_interface(raw.element_info.element, "ExpandCollapse").Expand()
        return
    except Exception:
        pass
    try:
        from detection.winforms_combo import expand_combo

        expand_combo(raw)
    except Exception:
        pass


def _read_control_value(raw) -> str:
    try:
        from pywinauto.uia_defines import get_elem_interface

        val = get_elem_interface(raw.element_info.element, "Value").CurrentValue
        if val:
            return str(val).strip()
    except Exception:
        pass
    try:
        from detection.uia_text import get_item_text

        return get_item_text(raw)
    except Exception:
        return ""


def _try_selection_item(item_raw, double_click: bool, x: int, y: int) -> Optional[dict]:
    if not item_raw:
        return None
    try:
        from pywinauto.uia_defines import get_elem_interface

        get_elem_interface(item_raw.element_info.element, "SelectionItem").Select()
        if double_click:
            from tools.input_tools import do_double_click

            do_double_click(x, y)
            return {"success": True, "method": "SelectionItem+double_click"}
        return {"success": True, "method": "SelectionItem"}
    except Exception:
        return None


def _activate_item(
    *,
    item_raw,
    item: dict,
    double_click: bool = False,
    window_title: Optional[str] = None,
) -> dict:
    from detection.element_coords import click_coords

    elem = dict(item)
    if window_title:
        from detection.element_coords import to_screen_coords

        elem = to_screen_coords(elem, window_title)
    x, y = click_coords(elem, window_title)
    sel = _try_selection_item(item_raw, double_click, x, y)
    if sel:
        sel["selected"] = item.get("name", "")
        return sel
    from tools.input_tools import do_click, do_double_click

    if double_click:
        do_double_click(x, y)
        return {"success": True, "method": "double_click", "selected": item.get("name", "")}
    do_click(x, y)
    return {"success": True, "method": "click_item", "selected": item.get("name", "")}


def _select_combo_descendants(raw, value: str) -> Optional[dict]:
    needle = (value or "").strip().lower()
    if not needle:
        return None
    try:
        from pywinauto.uia_defines import get_elem_interface
        from detection.backends.uia_backend import _pywinauto_to_element

        for child in raw.descendants():
            det = _pywinauto_to_element(child)
            if not det:
                continue
            name = (det.name or "").lower()
            if needle not in name:
                continue
            try:
                get_elem_interface(child.element_info.element, "SelectionItem").Select()
                verified = _read_control_value(raw)
                return {
                    "success": True,
                    "method": "SelectionItem",
                    "selected": det.name,
                    "verified_value": verified,
                }
            except Exception:
                continue
    except Exception:
        pass
    return None


def do_list_control_items(
    automation_id: str,
    filter_text: str = "",
    window_title: Optional[str] = None,
    offset: int = 0,
    limit: int = 50,
    expand: bool = True,
) -> dict[str, Any]:
    if sys.platform != "win32":
        return {"success": False, "error": "list_control_items is Windows-only"}
    raw, elem, _data, scope = _resolve_control(automation_id, window_title)
    if not raw or not elem:
        return {"success": False, "error": f"Control not found: {automation_id}"}

    scope = scope or {}
    role = (elem.role or "").lower()
    title = scope.get("resolved_title") or window_title

    if expand and role == "combobox":
        _expand_combo(raw)

    if role in ("table", "datagrid", "calendar"):
        from detection.grid_rows import collect_grid_rows

        batch = collect_grid_rows(raw, filter_text=filter_text, offset=offset, limit=limit)
        return {"success": True, "source": "grid_rows", **batch}

    from detection.uia_find import collect_control_items

    batch = collect_control_items(raw, filter_text=filter_text, offset=offset, limit=limit)
    source = "uia"
    if batch.get("matched_total", 0) == 0 and role == "combobox":
        from detection.winforms_combo import collect_combo_items

        wf = collect_combo_items(
            raw,
            filter_text=filter_text,
            offset=offset,
            limit=limit,
            combo_wrapper=raw,
        )
        if wf.get("matched_total", 0) > 0:
            batch = wf
            source = wf.get("source", "winforms_combo")
    return {"success": True, "source": source, **batch}


def do_select_control_item(
    automation_id: str,
    value: str,
    window_title: Optional[str] = None,
    double_click: bool = False,
    column: str = "",
) -> dict[str, Any]:
    if sys.platform != "win32":
        return {"success": False, "error": "select_control_item is Windows-only"}
    raw, elem, _data, scope = _resolve_control(automation_id, window_title)
    if not raw or not elem:
        return {"success": False, "error": f"Control not found: {automation_id}"}

    scope = scope or {}
    role = (elem.role or "").lower()
    title = scope.get("resolved_title") or window_title
    needle = (value or "").strip()
    if not needle:
        return {"success": False, "error": "value is required"}

    if role == "combobox":
        _expand_combo(raw)
        from detection.uia_find import collect_control_items, find_item_raw_by_name
        from detection.winforms_combo import (
            find_combo_item,
            item_requires_click_operation,
            click_target_for_item,
        )

        batch = collect_control_items(raw, filter_text=needle, limit=200)
        item_raw, item = find_item_raw_by_name(raw, needle)
        if not item:
            desc = _select_combo_descendants(raw, needle)
            if desc:
                return desc
            found = find_combo_item(raw, needle, combo_wrapper=raw)
            if found:
                item_raw, item = found
        if not item:
            return {"success": False, "error": f"Item not found matching '{needle}'"}
        if item_requires_click_operation(item):
            target = click_target_for_item(item)
            return {
                "success": False,
                "error": "Combo popup item requires explicit click operation",
                "requires_operation": "click",
                "click_at": target,
                "item": item.get("name", ""),
            }
        act = _activate_item(
            item_raw=item_raw,
            item=item,
            double_click=False,
            window_title=title,
        )
        if not act.get("success"):
            return act
        verified = _read_control_value(raw)
        act["verified_value"] = verified
        if needle.lower() not in (verified or "").lower() and batch.get("matched_total", 0) == 0:
            act["warning"] = "verify read-back does not contain needle"
        return act

    if role in ("table", "datagrid", "calendar"):
        from detection.grid_rows import find_grid_row
        from detection.uia_find import find_item_raw_by_name

        found = find_grid_row(raw, needle, column=column)
        if not found:
            item_raw, item = find_item_raw_by_name(raw, needle)
        else:
            item_raw, item = found
        if not item:
            return {"success": False, "error": f"Row not found matching '{needle}'"}
        act = _activate_item(
            item_raw=item_raw,
            item=item,
            double_click=double_click,
            window_title=title,
        )
        return act

    from detection.uia_find import find_item_raw_by_name

    item_raw, item = find_item_raw_by_name(raw, needle)
    if not item:
        return {"success": False, "error": f"Item not found matching '{needle}'"}
    return _activate_item(
        item_raw=item_raw,
        item=item,
        double_click=double_click,
        window_title=title,
    )


def do_get_grid_item(
    automation_id: str,
    row: int,
    column: int = 0,
    column_name: str = "",
    window_title: Optional[str] = None,
) -> dict[str, Any]:
    if sys.platform != "win32":
        return {"success": False, "error": "get_grid_item is Windows-only"}
    if row < 0:
        return {"success": False, "error": "row must be >= 0"}
    if column < 0:
        return {"success": False, "error": "column must be >= 0"}

    raw, elem, _data, scope = _resolve_control(automation_id, window_title)
    if not raw or not elem:
        return {"success": False, "error": f"Control not found: {automation_id}"}

    role = (elem.role or "").lower()
    if role not in ("table", "datagrid", "grid", "calendar", "list"):
        return {
            "success": False,
            "error": f"Control role '{elem.role}' is not a grid/table (automation_id={automation_id})",
        }

    from detection.grid_items import get_grid_item, public_grid_item

    item = get_grid_item(
        raw,
        row_index=int(row),
        column_index=int(column),
        column_name=column_name or "",
    )
    if not item:
        return {
            "success": False,
            "error": f"No cell at row={row} column={column}",
            "automation_id": automation_id,
        }

    payload = public_grid_item(item) or {}
    scope = scope or {}
    return {
        "success": True,
        "automation_id": automation_id,
        "resolved_window_title": scope.get("resolved_title") or window_title or "",
        **payload,
    }


def do_read_table(
    automation_id: str,
    filter_text: str = "",
    window_title: Optional[str] = None,
    offset: int = 0,
    limit: int = 200,
) -> dict[str, Any]:
    if sys.platform != "win32":
        return {"success": False, "error": "read_table is Windows-only"}
    if not (automation_id or "").strip():
        return {"success": False, "error": "automation_id is required"}
    if offset < 0:
        return {"success": False, "error": "offset must be >= 0"}

    raw, elem, _data, scope = _resolve_control(automation_id, window_title)
    if not raw or not elem:
        return {"success": False, "error": f"Control not found: {automation_id}"}

    role = (elem.role or "").lower()
    if role not in ("table", "datagrid", "grid", "calendar", "list"):
        return {
            "success": False,
            "error": (
                f"Control role '{elem.role}' is not a table/grid/list "
                f"(automation_id={automation_id})"
            ),
        }

    from detection.table_read import public_table_payload, read_table

    payload = read_table(
        raw,
        filter_text=filter_text or "",
        offset=int(offset or 0),
        limit=int(limit or 200),
    )
    public = public_table_payload(payload)
    if not public or not public.get("headers"):
        return {
            "success": False,
            "error": "No table data found (empty grid or unsupported layout)",
            "automation_id": automation_id,
        }

    scope = scope or {}
    return {
        "success": True,
        "automation_id": automation_id,
        "resolved_window_title": scope.get("resolved_title") or window_title or "",
        **public,
    }

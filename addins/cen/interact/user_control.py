"""cmdMoneda_UserControl and composite UserControl helpers."""
from __future__ import annotations

from typing import Any, Optional


def drill_user_control(
    automation_id: str = "",
    name: str = "",
    window_title: Optional[str] = None,
    max_depth: int = 6,
) -> dict[str, Any]:
    """List child controls inside a COBIS UserControl (e.g. cmdMoneda_UserControl1 → cmbMoneda)."""
    from tools.ui_automation import do_list_elements

    aid = (automation_id or name or "").strip()
    if not aid:
        return {"success": False, "error": "automation_id or name required"}

    listed = do_list_elements(window_title=window_title or "", max_depth=max_depth)
    if isinstance(listed, str):
        import json

        listed = json.loads(listed)

    children = []
    for el in listed.get("elements") or []:
        blob = f"{el.get('name') or ''} {el.get('automation_id') or ''}".lower()
        if aid.lower() in blob:
            children.append({"match": "container", **el})
        elif any(
            k in blob
            for k in ("cmbmoneda", "cmb", "txt", "msk", "lbl")
        ):
            if el.get("name") or el.get("automation_id"):
                children.append(el)

    combos = [c for c in children if (c.get("role") or "").lower() == "combobox" or "cmb" in (c.get("name") or "").lower()]
    return {
        "success": True,
        "user_control": aid,
        "child_count": len(children),
        "children": children[:40],
        "combos": combos[:5],
        "hint": "Use cen_set_moneda or list_control_items on cmbMoneda",
        "resolved_window_title": listed.get("resolved_window_title") or "",
    }


def set_moneda(
    value: str = "",
    index: int = -1,
    user_control: str = "cmdMoneda_UserControl1",
    window_title: Optional[str] = None,
) -> dict[str, Any]:
    """Select currency in cmdMoneda_UserControl via cmbMoneda combo."""
    from tools.ui_automation import do_click_element

    do_click_element(name=user_control, window_title=window_title or "")

    if index >= 0:
        from tools.control_items import do_select_control_item

        result = do_select_control_item(
            automation_id="cmbMoneda",
            name="cmbMoneda",
            index=index,
            window_title=window_title or "",
        )
    elif value:
        from tools.control_items import do_list_control_items, do_select_control_item

        items = do_list_control_items(name="cmbMoneda", window_title=window_title or "")
        pick = -1
        if isinstance(items, dict):
            for i, it in enumerate(items.get("items") or []):
                label = str(it.get("name") or it.get("text") or "")
                if value.lower() in label.lower():
                    pick = i
                    break
        if pick < 0:
            return {"success": False, "error": f"moneda '{value}' not in combo", "items": items}
        result = do_select_control_item(
            name="cmbMoneda",
            index=pick,
            window_title=window_title or "",
        )
    else:
        return {"success": False, "error": "value or index required"}

    ok = isinstance(result, dict) and result.get("success", True)
    return {
        "success": bool(ok),
        "user_control": user_control,
        "value": value,
        "index": index,
        "result": result,
    }

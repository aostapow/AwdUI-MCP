"""TriStateTreeView interaction (ADM seguridad permisos)."""
from __future__ import annotations

from typing import Any, Optional


def list_tristate_nodes(
    automation_id: str = "",
    name: str = "",
    window_title: Optional[str] = None,
    max_depth: int = 6,
) -> dict[str, Any]:
    """List TreeItem nodes under a TriStateTreeView (TV*, trv*)."""
    from tools.ui_automation import do_list_elements

    aid = automation_id or name
    if not aid:
        return {"success": False, "error": "automation_id or name required"}

    listed = do_list_elements(window_title=window_title or "", max_depth=max_depth)
    if isinstance(listed, str):
        import json

        listed = json.loads(listed)

    nodes = []
    for el in listed.get("elements") or []:
        role = (el.get("role") or "").lower()
        blob = f"{el.get('name') or ''} {el.get('automation_id') or ''}".lower()
        if role in ("treeitem", "tree item") or "treeitem" in role:
            nodes.append(
                {
                    "name": el.get("name"),
                    "automation_id": el.get("automation_id"),
                    "role": el.get("role"),
                }
            )
        elif aid.lower() in blob and role == "tree":
            nodes.append({"tree_root": el.get("name") or el.get("automation_id")})

    return {
        "success": True,
        "tree": aid,
        "node_count": len(nodes),
        "nodes": nodes[:200],
        "resolved_window_title": listed.get("resolved_window_title") or "",
        "hint": "Use cen_tristate_toggle with text_contains on node label",
    }


def toggle_tristate_node(
    automation_id: str = "",
    name: str = "",
    text_contains: str = "",
    window_title: Optional[str] = None,
    expand_first: bool = True,
) -> dict[str, Any]:
    """Toggle tri-state checkbox on tree node by partial text match."""
    if not text_contains:
        return {"success": False, "error": "text_contains required"}

    from tools.ui_automation import do_click_element, do_expand_element, do_find_element

    found = do_find_element(
        name=text_contains,
        window_title=window_title or "",
        fuzzy_match=True,
        include_offscreen=True,
    )
    if isinstance(found, str):
        import json

        found = json.loads(found)

    if not found.get("found") or not found.get("elements"):
        return {
            "success": False,
            "error": f"tree node matching '{text_contains}' not found",
            "tree": automation_id or name,
        }

    el = found["elements"][0]
    aid = el.get("automation_id") or ""
    nm = el.get("name") or ""

    if expand_first:
        try:
            do_expand_element(automation_id=aid or None, name=nm or None, window_title=window_title or "")
        except Exception:
            pass

    click = do_click_element(
        automation_id=aid or None,
        name=nm or None,
        window_title=window_title or "",
    )
    ok = isinstance(click, dict) and click.get("success", True)
    return {
        "success": bool(ok),
        "action": "toggle_tristate",
        "text_contains": text_contains,
        "element": el,
        "click_result": click,
        "note": "TriState cycles unchecked/partial/checked; verify in UI",
    }

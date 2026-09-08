"""Unified act API — resolve, hints, act, verify."""
from __future__ import annotations

from typing import Any, Optional


def do_act_on_control(
    action: str,
    automation_id: Optional[str] = None,
    name: Optional[str] = None,
    repo_path: Optional[str] = None,
    value: str = "",
    window_title: Optional[str] = None,
    verify_automation_id: Optional[str] = None,
    verify_contains: Optional[str] = None,
    verify: bool = False,
    window_handle: Optional[int] = None,
) -> dict[str, Any]:
    """Orchestrate resolve → act → optional verify for a control."""
    act = (action or "").strip().lower()
    if not act:
        return {"success": False, "error": "action is required (invoke|click|set|select)"}

    from detection.hint_consume import attach_hints_to_result, resolve_object_hints
    from tools.ui_automation import (
        do_click_element,
        do_find_element,
        do_invoke_element,
        do_set_element_value,
    )
    from tools.control_items import do_select_control_item

    resolved_aid = automation_id
    resolved_name = name
    if (repo_path or "").strip():
        from tools.repo_action import do_repo_resolve

        resolved = do_repo_resolve(repo_path, window_title)
        if not resolved.get("found"):
            return {"success": False, "error": resolved.get("error", "repo resolve failed")}
        elem = resolved.get("element") or {}
        resolved_aid = elem.get("automation_id") or automation_id
        resolved_name = elem.get("name") or name

    hints_ctx = resolve_object_hints(repo_path=repo_path, automation_id=resolved_aid)
    verify_aid = verify_automation_id or hints_ctx.get("hint_verify_automation_id")
    verify_name = verify_contains

    timing_ms = 0
    if act == "invoke":
        result = do_invoke_element(
            name=resolved_name,
            automation_id=resolved_aid,
            window_title=window_title,
            window_handle=window_handle,
            repo_path=repo_path,
            verify_automation_id=verify_aid,
            verify_name_contains=verify_name,
        )
        acted_via = result.get("method", "invoke")
    elif act == "click":
        result = do_click_element(
            name=resolved_name,
            automation_id=resolved_aid,
            window_title=window_title,
            window_handle=window_handle,
            repo_path=repo_path,
            verify_automation_id=verify_aid,
            verify_name_contains=verify_name,
        )
        acted_via = result.get("method", "click")
    elif act == "set":
        result = do_set_element_value(
            value=value,
            name=resolved_name,
            automation_id=resolved_aid,
            window_title=window_title,
            window_handle=window_handle,
            verify=verify,
        )
        acted_via = "set_element_value"
    elif act == "select":
        if not (resolved_aid or "").strip():
            return {"success": False, "error": "automation_id required for select action"}
        result = do_select_control_item(
            resolved_aid,
            value,
            window_title=window_title,
        )
        acted_via = "select_control_item"
    else:
        return {"success": False, "error": f"unsupported action: {action}"}

    timing_ms = int(result.get("elapsed_ms") or (result.get("timing") or {}).get("operational_ms") or 0)
    out: dict[str, Any] = {
        "success": bool(result.get("success")),
        "acted_via": acted_via,
        "hints_applied": hints_ctx.get("hint_parsed") or {},
        "verified": result.get("verified"),
        "timing_ms": timing_ms,
    }
    for key, val in result.items():
        if key not in out:
            out[key] = val
    attach_hints_to_result(out, repo_path=repo_path, automation_id=resolved_aid)
    if verify and act in ("invoke", "click") and verify_name and out.get("success"):
        if out.get("verified") is False:
            out["success"] = False
            out.setdefault("error", "verify failed after act_on_control")
    return out

"""Apply repository agent_hints when resolving or acting on controls."""
from __future__ import annotations

from typing import Any, Optional

from detection.agent_hints import (
    hint_click_mode,
    hint_preferred_tool,
    hint_verify_automation_id,
    parse_agent_hints,
)


def resolve_object_hints(
    *,
    repo_path: Optional[str] = None,
    automation_id: Optional[str] = None,
) -> dict[str, Any]:
    """Load hints for an object (repo_path first, then automation_id)."""
    hints = ""
    if (repo_path or "").strip():
        try:
            from detection.repo_store import get_agent_hints

            hints = get_agent_hints(repo_path.strip())
        except Exception:
            hints = ""
    aid = (automation_id or "").strip()
    if not hints.strip() and aid:
        try:
            from detection.repo_store import get_hints_by_automation_id

            hints = get_hints_by_automation_id(aid)
        except Exception:
            hints = ""
    parsed = parse_agent_hints(hints) if hints.strip() else {}
    preferred = hint_preferred_tool(hints) if hints.strip() else None
    return {
        "agent_hints": hints,
        "hint_parsed": parsed,
        "hint_preferred_tool": preferred,
        "hint_verify_automation_id": hint_verify_automation_id(hints) if hints.strip() else None,
        "hint_click_mode": hint_click_mode(hints) if hints.strip() else "auto",
    }


def attach_hints_to_result(
    result: dict[str, Any],
    *,
    repo_path: Optional[str] = None,
    automation_id: Optional[str] = None,
) -> dict[str, Any]:
    """Merge hint context into a find/resolve result dict."""
    if not isinstance(result, dict):
        return result
    path = (repo_path or result.get("repo_path") or "").strip() or None
    aid = (automation_id or "").strip()
    if not aid:
        elements = result.get("elements") or []
        if elements and isinstance(elements[0], dict):
            aid = (elements[0].get("automation_id") or "").strip() or None
    ctx = resolve_object_hints(repo_path=path, automation_id=aid)
    if not (ctx.get("agent_hints") or "").strip():
        return result
    result["agent_hints"] = ctx["agent_hints"]
    if ctx.get("hint_parsed"):
        result["hint_parsed"] = ctx["hint_parsed"]
    if ctx.get("hint_preferred_tool"):
        result["hint_preferred_tool"] = ctx["hint_preferred_tool"]
    if ctx.get("hint_verify_automation_id"):
        result["hint_verify_automation_id"] = ctx["hint_verify_automation_id"]
    if ctx.get("hint_click_mode") and ctx["hint_click_mode"] != "auto":
        result["hint_click_mode"] = ctx["hint_click_mode"]
    return result


def apply_hints_to_discovery_report(report: dict[str, Any], hints: str) -> dict[str, Any]:
    """Attach hints and promote recommended strategy when metodo_preferido matches a tool."""
    text = (hints or "").strip()
    if not text:
        return report
    report["repo_hints"] = text
    parsed = parse_agent_hints(text)
    if parsed:
        report["repo_parsed"] = parsed
    preferred = hint_preferred_tool(text)
    if not preferred:
        return report
    report["hint_preferred_tool"] = preferred
    strategies = report.get("strategies") or []
    act = [s for s in strategies if s.get("phase") != "read"]
    match = next((s for s in act if preferred in (s.get("tools") or [])), None)
    if not match:
        return report
    promoted = dict(match)
    promoted["confidence"] = "high"
    note = (promoted.get("note") or "").strip()
    promo_note = f"repo hint → {preferred}"
    promoted["note"] = f"{note}; {promo_note}" if note else promo_note
    report["recommended"] = promoted
    report["hint_applied"] = "recommended_strategy"
    return report


def apply_hint_click_mode(
    *,
    elem: dict,
    click_mode: str,
    invoke_fn,
    click_fn,
    identifiable_by_properties_fn=None,
) -> dict[str, Any]:
    """Choose invoke vs coordinate click per repo hint (shared with repo_action)."""
    mode = (click_mode or "auto").strip().lower()
    if mode == "click":
        out = click_fn()
        if out.get("success"):
            out["hint_applied"] = "click_mode=click"
        return out

    inv = invoke_fn()
    if inv.get("success"):
        out = dict(inv)
        if mode == "invoke":
            out["hint_applied"] = "invoke_mode=invoke"
        return out

    if mode == "invoke":
        return {
            "success": False,
            "error": "InvokePattern failed; repo hint requests invoke only (no coordinate click)",
            "hint_applied": "invoke_mode=invoke",
        }

    if identifiable_by_properties_fn and identifiable_by_properties_fn(elem):
        return {
            "success": False,
            "error": (
                "Element resolved by properties but InvokePattern failed; "
                "coordinate click skipped"
            ),
        }
    return click_fn()

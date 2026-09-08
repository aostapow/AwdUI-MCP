"""Bridge to awdui-spy-sidecar for Spy-grade inspection."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional


def _sidecar_exe() -> Optional[Path]:
    p = Path(__file__).resolve().parents[2] / "awdui-spy-sidecar" / "publish" / "awdui-spy-sidecar.exe"
    return p if p.exists() else None


def _enrich_window_params(params: dict) -> dict:
    """Attach UWP-aware HWND so sidecar attaches to CoreWindow."""
    from tools.target_window import get_target
    from tools.windows import resolve_window_handle, resolve_window_visual_rect

    title = (params.get("window_title") or get_target() or "").strip()
    if title:
        params["window_title"] = title
        hwnd = resolve_window_handle(title)
        if hwnd:
            params["hwnd"] = hwnd
        visual = resolve_window_visual_rect(title)
        if visual:
            params["window_rect"] = visual
    return params


def _call(command: str, params: dict) -> dict:
    exe = _sidecar_exe()
    if not exe:
        return {"found": False, "error": "awdui-spy-sidecar not built"}
    params = _enrich_window_params(dict(params))
    req = json.dumps({"Command": command, "Params": params})
    try:
        proc = subprocess.run(
            [str(exe)],
            input=req,
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if proc.stdout.strip():
            return json.loads(proc.stdout.strip())
        return {"found": False, "error": proc.stderr or "no output"}
    except Exception as exc:
        return {"found": False, "error": str(exc)}


def spy_inspect_at(x: int, y: int) -> dict:
    return _call("from_point", {"x": x, "y": y})


def spy_inspect_element(
    name: Optional[str] = None,
    automation_id: Optional[str] = None,
    window_title: Optional[str] = None,
) -> dict:
    return _call("inspect_full", {
        "name": name or "",
        "automation_id": automation_id or "",
        "window_title": window_title or "",
    })


def spy_tree(
    window_title: str = "",
    mode: str = "control",
    max_depth: int = 0,
    visible_only: bool = False,
    role_filter: str = "",
) -> dict:
    return _call("walk_tree", {
        "window_title": window_title,
        "mode": mode,
        "max_depth": max_depth,
        "visible_only": visible_only,
        "role": role_filter,
    })


def _normalize_role(role: str) -> str:
    return (role or "").replace("ControlType.", "")


def _value_from_spy_patterns(patterns: object) -> str:
    """Extract ValuePattern text from spy sidecar patterns dict."""
    if not isinstance(patterns, dict):
        return ""
    vp = patterns.get("Value") or patterns.get("value")
    if isinstance(vp, dict):
        return str(vp.get("value") or "")
    return ""


def spy_props_to_element(props: dict, window_title: Optional[str] = None) -> dict:
    """Convert spy sidecar properties to legacy element dict."""
    x = int(props.get("x", 0) or 0)
    y = int(props.get("y", 0) or 0)
    w = int(props.get("width", 0) or 0)
    h = int(props.get("height", 0) or 0)
    role = _normalize_role(str(props.get("role", "")))
    elem = {
        "name": props.get("name", "") or "",
        "role": role,
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "value": _value_from_spy_patterns(props.get("patterns")),
        "automation_id": props.get("automation_id", "") or "",
        "class_name": props.get("class_name", "") or "",
        "framework_id": props.get("framework_id", "") or "",
        "process_id": int(props.get("process_id", 0) or 0),
        "visible": not bool(props.get("is_offscreen")),
        "enabled": bool(props.get("is_enabled", True)),
        "backend": "spy",
        "patterns": list((props.get("patterns") or {}).keys()),
    }
    if window_title:
        from detection.element_coords import to_screen_coords

        return to_screen_coords(elem, window_title)
    elem["clickable_x"] = x + w // 2 if w else x
    elem["clickable_y"] = y + h // 2 if h else y
    return elem


def spy_invoke_element(
    name: Optional[str] = None,
    automation_id: Optional[str] = None,
    window_title: Optional[str] = None,
) -> dict:
    """Activate via FlaUI sidecar: InvokePattern or SelectionItemPattern (UWP NavView)."""
    if not (name or automation_id):
        return {"success": False, "error": "name or automation_id required"}
    return _call("invoke", {
        "name": name or "",
        "automation_id": automation_id or "",
        "window_title": window_title or "",
    })


def spy_verify_live(
    automation_id: str,
    window_title: Optional[str] = None,
    require_enabled: bool = True,
) -> dict:
    """Pre-flight: spy inspect without pywinauto cache — detect stale/disabled controls."""
    if not automation_id:
        return {"live": False, "code": "stale_instance", "reason": "no_automation_id"}
    hit = spy_inspect_element(automation_id=automation_id, window_title=window_title)
    if not hit.get("found"):
        return {"live": False, "code": "stale_instance", "reason": "not_found"}
    props = hit.get("properties") or {}
    enabled = bool(props.get("is_enabled", True))
    pid = int(props.get("process_id", 0) or 0)
    if require_enabled and not enabled:
        return {
            "live": False,
            "code": "stale_instance",
            "reason": "disabled",
            "process_id": pid,
            "automation_id": automation_id,
        }
    return {"live": True, "process_id": pid, "enabled": enabled}


def spy_expand_collapse_element(
    name: Optional[str] = None,
    automation_id: Optional[str] = None,
    window_title: Optional[str] = None,
    action: str = "expand",
) -> dict:
    """Expand or collapse via FlaUI ExpandCollapsePattern."""
    if not (name or automation_id):
        return {"success": False, "error": "name or automation_id required"}
    return _call("expand_collapse", {
        "name": name or "",
        "automation_id": automation_id or "",
        "window_title": window_title or "",
        "action": action or "expand",
    })


def spy_find_element(
    name: Optional[str] = None,
    automation_id: Optional[str] = None,
    window_title: Optional[str] = None,
    role: Optional[str] = None,
) -> Optional[dict]:
    """Fast FlaUI FindFirstDescendant — same engine as Automation Spy."""
    if not (name or automation_id):
        return None
    result = spy_inspect_element(
        name=name,
        automation_id=automation_id,
        window_title=window_title,
    )
    if not result.get("found"):
        return None
    elem = spy_props_to_element(result.get("properties") or {}, window_title=window_title)
    if role and role.lower() not in (elem.get("role") or "").lower():
        return None
    return elem


def spy_list_elements(
    window_title: str = "",
    max_depth: int = 0,
    role_filter: str = "",
    visible_only: bool = False,
) -> list[dict]:
    """Full tree walk via spy sidecar (FlaUI)."""
    result = spy_tree(
        window_title=window_title,
        max_depth=max_depth,
        role_filter=role_filter,
        visible_only=visible_only,
    )
    return [spy_props_to_element(p, window_title=window_title) for p in result.get("elements", [])]


def spy_available() -> bool:
    return _sidecar_exe() is not None

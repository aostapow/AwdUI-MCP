"""Bridge to awdui-spy-sidecar for Spy-grade inspection."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional


def _sidecar_exe() -> Optional[Path]:
    p = Path(__file__).resolve().parents[2] / "awdui-spy-sidecar" / "publish" / "awdui-spy-sidecar.exe"
    return p if p.exists() else None


def _call(command: str, params: dict) -> dict:
    exe = _sidecar_exe()
    if not exe:
        return {"found": False, "error": "awdui-spy-sidecar not built"}
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
    max_depth: int = 12,
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
        "value": "",
        "automation_id": props.get("automation_id", "") or "",
        "class_name": props.get("class_name", "") or "",
        "framework_id": props.get("framework_id", "") or "",
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
    max_depth: int = 12,
    role_filter: str = "",
) -> list[dict]:
    """Full tree walk via spy sidecar (FlaUI)."""
    result = spy_tree(
        window_title=window_title,
        max_depth=max_depth,
        role_filter=role_filter,
    )
    return [spy_props_to_element(p, window_title=window_title) for p in result.get("elements", [])]


def spy_available() -> bool:
    return _sidecar_exe() is not None

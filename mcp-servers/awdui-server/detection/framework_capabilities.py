"""Framework × tool capability matrix for agent guidance and prechecks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

# Framework + control role overrides (tool_name -> level, use_instead).
_FRAMEWORK_ROLE_OVERRIDES: dict[tuple[str, str, str], tuple[str, str]] = {
    ("winforms", "combobox", "set_element_value"): (
        "blocked",
        "list_control_items + select_control_item",
    ),
    ("winforms", "button", "invoke_element"): (
        "discouraged",
        "click_element",
    ),
    ("win32", "menuitem", "click_element"): (
        "discouraged",
        "invoke_element or send_keys (menu must be open)",
    ),
    ("uwp", "listitem", "invoke_element"): (
        "conditional",
        "verify_name_contains may need Header.contains; prefer visible nodes",
    ),
}

# Default tool levels per framework (tool_name -> level).
_FRAMEWORK_TOOL_LEVELS: dict[str, dict[str, str]] = {
    "winforms": {
        "screenshot_window": "preferred",
        "find_element": "preferred",
        "invoke_element": "preferred",
        "set_element_value": "preferred",
    },
    "wpf": {
        "screenshot_window": "preferred",
        "find_element": "preferred",
    },
    "win32": {
        "find_element": "preferred",
        "invoke_element": "preferred",
        "send_keys": "preferred",
        "list_elements": "preferred",
    },
    "qt": {
        "find_element": "preferred",
        "find_text": "conditional",
        "click_text": "conditional",
    },
    "uwp": {
        "screenshot_window": "blocked",
        "find_element": "preferred",
        "smart_find": "preferred",
        "list_elements": "preferred",
    },
    "electron": {
        "screenshot_window": "blocked",
        "find_element": "conditional",
    },
    "java_swing": {
        "find_element": "blocked",
        "click_element": "blocked",
        "invoke_element": "blocked",
    },
    "gtk": {
        "find_element": "blocked",
    },
}

_FRAMEWORK_PRIORITY: dict[str, int] = {
    "winforms": 30,
    "wpf": 25,
    "uwp": 20,
    "electron": 15,
    "win32": 10,
    "unknown": 0,
}


@dataclass(frozen=True)
class ToolCapability:
    level: str
    reason: str = ""


def _normalize_framework(framework: str) -> str:
    return (framework or "unknown").strip().lower()


def _normalize_role(control_role: Optional[str]) -> str:
    return (control_role or "").strip().lower()


def merge_framework(existing: str, new: str) -> str:
    """Prefer a known framework label over ``unknown`` or weaker guesses."""
    cur = _normalize_framework(existing)
    incoming = _normalize_framework(new)
    if cur in ("", "unknown"):
        return incoming or "unknown"
    if incoming in ("", "unknown"):
        return cur
    if _FRAMEWORK_PRIORITY.get(incoming, 0) > _FRAMEWORK_PRIORITY.get(cur, 0):
        return incoming
    return cur


def get_tool_capability(
    framework: str,
    tool_name: str,
    *,
    app_storage_key: Optional[str] = None,
    control_role: Optional[str] = None,
) -> ToolCapability:
    fw = _normalize_framework(framework)
    tool = (tool_name or "").strip()

    if control_role:
        role = _normalize_role(control_role)
        override = _FRAMEWORK_ROLE_OVERRIDES.get((fw, role, tool))
        if override:
            level, use_instead = override
            return ToolCapability(level, use_instead)

    level = _FRAMEWORK_TOOL_LEVELS.get(fw, {}).get(tool, "allowed")
    return ToolCapability(level)


def check_tool_capability(
    framework: str,
    tool_name: str,
    *,
    control_role: Optional[str] = None,
    app_storage_key: Optional[str] = None,
) -> dict[str, Any]:
    cap = get_tool_capability(
        framework,
        tool_name,
        app_storage_key=app_storage_key,
        control_role=control_role,
    )
    out: dict[str, Any] = {
        "level": cap.level,
        "blocked": cap.level == "blocked",
        "warning": cap.level in ("discouraged", "conditional"),
    }
    if cap.reason:
        out["reason"] = cap.reason
        if cap.level == "blocked":
            out["use_instead"] = cap.reason
    return out


def printwindow_capability(framework: str) -> dict[str, Any]:
    cap = get_tool_capability(_normalize_framework(framework), "screenshot_window")
    compatible = cap.level not in ("blocked",)
    return {"compatible": compatible, "level": cap.level, "reason": cap.reason}


def build_automation_profile(
    *,
    window_title: str = "",
    app_name: str = "",
    exe_path: str = "",
    repo_framework: str = "unknown",
    detected_framework: str = "unknown",
) -> dict[str, Any]:
    fw = merge_framework(detected_framework, repo_framework)
    storage = (app_name or "").strip()
    if "\\" in storage:
        storage = storage.rsplit("\\", 1)[-1]

    preferred_tools: list[str] = []
    blocked_tools: list[str] = []
    for tool, level in _FRAMEWORK_TOOL_LEVELS.get(fw, {}).items():
        if level == "preferred":
            preferred_tools.append(tool)
        elif level == "blocked":
            blocked_tools.append(tool)

    notes: list[str] = []
    app_label = (app_name or window_title or "Application").rsplit(".", 1)[0]

    if fw == "winforms":
        notes.append("Prefer UIA patterns and AutomationId on WinForms controls.")
        notes.append("ComboBox: list_control_items + select_control_item (not set_element_value).")
        notes.append("Lookup modals: complete sub-flow in dialog before returning to parent.")
    elif fw == "uwp":
        notes.append(
            "UWP apps may expose multiple HWNDs (ApplicationFrameHost vs core); "
            "prefer core process for UIA attach and frame host for screenshots."
        )
        notes.append("Flyouts and title chrome may be separate top-level windows — check active window.")
        notes.append("NavView: use include_offscreen=true only for discovery; act on visible controls.")
    elif fw == "win32":
        notes.append("Menus are only in the UIA tree while open — use Alt+letter or expand first.")
        notes.append("Modal dialogs (#32770): set scope to modal HWND before find/act.")
    elif fw == "qt":
        notes.append("Standard Qt widgets are UIA-accessible; QML/QtQuick needs Accessible{} declarations.")
        notes.append("Custom QWidgets without QAccessibleInterface require find_text/OCR fallback.")

    tools: dict[str, dict[str, Any]] = {}
    for tool in sorted(
        {*preferred_tools, *blocked_tools, "invoke_element", "find_element", "set_element_value"}
    ):
        tools[tool] = check_tool_capability(fw, tool, app_storage_key=storage)

    return {
        "framework": fw,
        "app_name": app_name,
        "exe_path": exe_path,
        "window_title": window_title,
        "app_label": app_label,
        "notes": notes,
        "preferred_tools": preferred_tools,
        "blocked_tools": blocked_tools,
        "tools": tools,
    }


def capability_precheck(window_title: str, tool_name: str) -> Optional[dict[str, Any]]:
    """Return a blocking error dict when a tool must not run on this target."""
    from tools.framework_detect import do_detect_framework
    from detection.app_identity import repository_app_name

    detected = do_detect_framework(window_title or "")
    fw = _normalize_framework(detected.get("framework", "unknown"))
    app_name, _exe = repository_app_name(fw, window_title or "")
    storage = (app_name or "").strip()
    if "\\" in storage:
        storage = storage.rsplit("\\", 1)[-1]

    if fw == "java_swing" and tool_name == "find_element":
        return {
            "success": False,
            "error": "find_element is blocked for java_swing — enable JAB or use OCR",
            "framework": fw,
            "tool": tool_name,
        }

    cap = check_tool_capability(fw, tool_name, app_storage_key=storage)
    if cap.get("blocked"):
        return {
            "success": False,
            "error": cap.get("reason") or f"{tool_name} blocked for {fw}",
            "framework": fw,
            "tool": tool_name,
            "use_instead": cap.get("use_instead", ""),
        }
    return None


def attach_automation_profile(detected: dict[str, Any]) -> dict[str, Any]:
    """Merge framework capability matrix into a detect_framework result dict."""
    from detection.app_identity import repository_app_name

    title = (detected.get("window_title") or "").strip()
    fw = _normalize_framework(detected.get("framework", "unknown"))
    app_name = (detected.get("app_name") or "").strip()
    exe_path = (detected.get("exe_path") or "").strip()

    if not app_name:
        app_name, exe_path = repository_app_name(fw, title)

    repo_fw = fw
    try:
        from detection.object_repository import load_repo

        repo = load_repo(app_name, exe_path) or {}
        repo_fw = merge_framework(fw, repo.get("framework") or fw)
    except Exception:
        pass

    profile = build_automation_profile(
        window_title=title,
        app_name=app_name,
        exe_path=exe_path,
        detected_framework=fw,
        repo_framework=repo_fw,
    )
    profile["uia_support"] = detected.get("uia_support", "unknown")
    detected["automation_profile"] = profile
    return detected


def format_automation_profile_lines(profile: dict[str, Any]) -> list[str]:
    """Human-readable lines for MCP text output."""
    lines = ["", "Automation profile:"]
    if profile.get("notes"):
        lines.append("  Notes:")
        for note in profile["notes"]:
            lines.append(f"    - {note}")
    preferred = profile.get("preferred_tools") or []
    blocked = profile.get("blocked_tools") or []
    if preferred:
        lines.append(f"  Preferred tools: {', '.join(preferred)}")
    if blocked:
        lines.append(f"  Blocked tools: {', '.join(blocked)}")
    tools = profile.get("tools") or {}
    flagged = [
        (name, info)
        for name, info in sorted(tools.items())
        if info.get("level") in ("blocked", "discouraged", "conditional")
    ]
    if flagged:
        lines.append("  Tool cautions:")
        for name, info in flagged:
            level = info.get("level", "")
            reason = info.get("reason") or info.get("use_instead") or ""
            suffix = f" — {reason}" if reason else ""
            lines.append(f"    - {name}: {level}{suffix}")
    return lines

"""Framework × tool capability matrix for agent guidance and prechecks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

# Repo-known apps whose live framework may disagree with a wrong detector label.
_REPO_APP_FRAMEWORK: dict[str, str] = {
    "administrador.exe": "winforms",
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
    "uwp": {
        "screenshot_window": "blocked",
        "find_element": "preferred",
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

# App-specific control overrides: (storage_key, role, tool) -> (level, use_instead)
_CONTROL_OVERRIDES: dict[tuple[str, str, str], tuple[str, str]] = {
    ("administrador.exe", "combobox", "set_element_value"): (
        "blocked",
        "list_control_items + select_control_item",
    ),
    ("administrador.exe", "button", "invoke_element"): (
        "discouraged",
        "click_element",
    ),
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


def _normalize_storage_key(app_storage_key: Optional[str]) -> str:
    key = (app_storage_key or "").strip().lower()
    if "\\" in key:
        key = key.rsplit("\\", 1)[-1]
    return key


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
    storage = _normalize_storage_key(app_storage_key)

    if storage and storage in _REPO_APP_FRAMEWORK:
        known = _REPO_APP_FRAMEWORK[storage]
        if fw != known and fw not in ("", "unknown"):
            return ToolCapability(
                "conditional",
                f"repository indicates {known}, not {fw}",
            )

    if storage and control_role:
        role = control_role.strip().lower()
        override = _CONTROL_OVERRIDES.get((storage, role, tool))
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
) -> dict[str, Any]:
    fw = merge_framework(repo_framework, repo_framework)
    storage = _normalize_storage_key(app_name)
    if storage in _REPO_APP_FRAMEWORK:
        fw = merge_framework(fw, _REPO_APP_FRAMEWORK[storage])

    preferred_tools: list[str] = []
    blocked_tools: list[str] = []
    for tool, level in _FRAMEWORK_TOOL_LEVELS.get(fw, {}).items():
        if level == "preferred":
            preferred_tools.append(tool)
        elif level == "blocked":
            blocked_tools.append(tool)

    notes: list[str] = []
    if storage == "administrador.exe" or "ast" in (window_title or "").lower():
        notes.append("AST Activities Manager is WinForms — not Electron.")
        app_label = "AST Activities Manager"
    else:
        app_label = (app_name or window_title or "Application").rsplit(".", 1)[0]

    if fw == "winforms":
        notes.append("Prefer UIA patterns and AutomationId on WinForms controls.")

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
    storage = _normalize_storage_key(app_name)

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

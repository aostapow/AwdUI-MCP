"""MCP tools for framework automation profiles."""
from __future__ import annotations

from typing import Any

from detection.framework_capabilities import (
    attach_automation_profile,
    format_automation_profile_lines,
)


def do_get_automation_profile(window_title: str = "") -> dict[str, Any]:
    """Return preferred/blocked tools and notes for the target window."""
    from tools.framework_detect import do_detect_framework

    title = (window_title or "").strip()
    detected = do_detect_framework(title)
    profile = detected.get("automation_profile")
    if not profile:
        detected = attach_automation_profile(detected)
        profile = detected.get("automation_profile") or {}
    return {
        **profile,
        "detected_framework": detected.get("framework", "unknown"),
        "uia_support": detected.get("uia_support", "unknown"),
        "process_name": detected.get("process_name", ""),
        "hints": detected.get("hints") or [],
    }


def register(server) -> int:
    """Register get_automation_profile MCP tool."""

    @server.tool()
    def get_automation_profile(window_title: str = "", title: str = "") -> str:
        """Get automation profile for a window: preferred/blocked MCP tools and framework notes.

        Complements detect_framework with the capability matrix (tools per framework,
        role overrides). Use before planning UIA actions on partial frameworks
        (WinForms, UWP, Win32, Qt).

        Parameters:
            window_title: Partial title of the target window (default: foreground).
            title: Alias for window_title.
        """
        from tools.params import resolve_window_title

        profile = do_get_automation_profile(resolve_window_title(window_title, title))
        lines = [
            f"Framework: {profile.get('framework', 'unknown')}",
            f"UIA support: {profile.get('uia_support', 'unknown')}",
            f"App: {profile.get('app_label') or profile.get('app_name', '')}",
        ]
        lines.extend(format_automation_profile_lines(profile))
        if profile.get("hints"):
            lines.extend(["", "Detection hints:"])
            for hint in profile["hints"]:
                lines.append(f"  - {hint}")
        return "\n".join(lines)

    return 1

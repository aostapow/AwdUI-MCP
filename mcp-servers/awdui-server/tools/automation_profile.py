"""MCP-facing automation profile built from framework capability matrix."""
from __future__ import annotations

from typing import Any, Optional

from detection.framework_capabilities import build_automation_profile


def do_get_automation_profile(window_title: str = "") -> dict[str, Any]:
    """Return preferred/blocked tools and notes for the target window."""
    from detection.app_identity import repository_app_name
    from detection.object_repository import load_repo
    from tools.framework_detect import do_detect_framework

    title = (window_title or "").strip()
    detected = do_detect_framework(title)
    fw_label = detected.get("framework", "unknown")
    app_name, exe_path = repository_app_name(fw_label, title)
    repo = load_repo(app_name, exe_path) or {}
    repo_fw = repo.get("framework") or fw_label

    profile = build_automation_profile(
        window_title=title,
        app_name=app_name,
        exe_path=exe_path,
        repo_framework=repo_fw,
    )
    profile["detected_framework"] = fw_label
    profile["process_name"] = detected.get("process_name") or app_name
    profile["hints"] = detected.get("hints") or []
    return profile

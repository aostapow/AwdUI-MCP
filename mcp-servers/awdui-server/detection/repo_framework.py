"""Repository framework detection, merge rules, and refresh helpers."""
from __future__ import annotations

from typing import Any, Optional

from detection.framework_capabilities import merge_framework


def detect_framework_label(window_title: str) -> str:
    from tools.framework_detect import do_detect_framework

    return do_detect_framework(window_title or "").get("framework", "unknown")


def guess_window_title_for_app(
    app: dict[str, Any],
    *,
    conn=None,
    windows: Optional[list[dict]] = None,
) -> str:
    """Pick the best live window title for a stored application record."""
    from tools.windows import do_list_windows

    live = windows if windows is not None else do_list_windows()
    app_name = (app.get("app_name") or "").strip()
    app_lower = app_name.lower()
    stem = app_lower.rsplit(".", 1)[0] if app_lower else ""

    window_keys: list[str] = []
    if conn is not None:
        rows = conn.execute(
            "SELECT window_key FROM windows WHERE app_id=?",
            (app.get("app_id"),),
        ).fetchall()
        window_keys = [str(r["window_key"]) for r in rows]

    exact_proc: list[str] = []
    key_match: list[str] = []
    fuzzy: list[str] = []
    for win in live:
        title = win.get("title") or ""
        proc = (win.get("process_name") or "").lower()
        if proc == app_lower:
            exact_proc.append(title)
        elif stem and stem in proc:
            exact_proc.append(title)
        elif any(k and k.lower() in title.lower() for k in window_keys):
            key_match.append(title)
        elif stem and stem in title.lower():
            fuzzy.append(title)

    if exact_proc:
        return exact_proc[0]
    if key_match:
        return key_match[0]
    if fuzzy:
        return fuzzy[0]
    return ""


def refresh_app_framework(app_id_value: str, db_path=None) -> dict[str, Any]:
    from detection import repo_store

    detail = repo_store.get_application(app_id_value, db_path=db_path)
    if not detail:
        return {"success": False, "error": "application not found"}

    title = guess_window_title_for_app(detail)
    if not title:
        return {"success": False, "error": "no matching window title"}

    framework = detect_framework_label(title)
    updated = repo_store.update_application(
        app_id_value,
        framework=framework,
        db_path=db_path,
    )
    return {
        "success": True,
        "app_id": app_id_value,
        "framework": updated.get("framework", framework),
        "window_title": title,
    }

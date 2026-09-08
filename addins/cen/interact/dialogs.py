"""COBIS message box and dialog helpers."""
from __future__ import annotations

from typing import Any, Optional


def detect_message_box(window_title: Optional[str] = None) -> dict[str, Any]:
    from tools.windows import do_list_windows

    dialogs = []
    for win in do_list_windows():
        title = (win.get("title") or "").lower()
        cls = (win.get("class_name") or "").lower()
        if "#32770" in cls or "dialog" in cls or title in ("", "cobis"):
            if win.get("width", 0) < 900:
                dialogs.append(win)
    return {"success": True, "dialogs": dialogs[:5], "count": len(dialogs)}


def handle_dialog(
    action: str = "ok",
    text_match: str = "",
    window_title: Optional[str] = None,
    auto_classify: bool = True,
) -> dict[str, Any]:
    from tools.input_tools import do_press_key
    from tools.ui_automation import do_click_element, do_find_element

    if text_match:
        found = do_find_element(name=text_match, window_title=window_title or "")
        if isinstance(found, dict) and found.get("found"):
            return do_click_element(name=text_match, window_title=window_title or "")

    resolved_action = action
    classification = None
    if auto_classify and action.lower() in ("ok", "auto"):
        from detect.messages import match_dialog_from_ui

        classification = match_dialog_from_ui(window_title)
        if classification.get("success"):
            resolved_action = classification.get("suggested_action", action)

    key = "ENTER" if resolved_action.lower() in ("ok", "yes", "si", "sí") else "ESCAPE"
    key_result = do_press_key(key)
    return {
        "success": True,
        "action": resolved_action,
        "key": key,
        "key_result": key_result,
        "classification": classification,
    }

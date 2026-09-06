"""Autonomous recovery when integration steps stall or unexpected UI appears."""
from __future__ import annotations

import time
from typing import Any, Callable, Optional

BLOCKER_TITLE_KEYWORDS = (
    "error", "actualización", "update", "privacy", "privacidad",
    "microsoft store", "desea", "guardar", "save", "permiso", "permission",
)

DISMISS_NAMES = ("ok", "cancel", "cerrar", "close", "aceptar", "no", "sí", "si")


def detect_blockers(window_title: str) -> list[dict]:
    from tools.windows import do_list_windows

    blockers: list[dict] = []
    target_lower = (window_title or "").lower()
    for win in do_list_windows():
        title = (win.get("title") or "").strip()
        if not title:
            continue
        title_lower = title.lower()
        if target_lower and target_lower in title_lower:
            continue
        proc = (win.get("process_name") or "").lower()
        if proc in ("python.exe", "pythonw.exe", "cursor.exe"):
            continue
        if any(k in title_lower for k in BLOCKER_TITLE_KEYWORDS):
            blockers.append({"type": "dialog", "title": title, "window": win})
        elif title and title_lower not in ("program manager", "desktop"):
            blockers.append({"type": "foreign_window", "title": title, "window": win})
    return blockers


def _try_dismiss_dialogs(window_title: str) -> bool:
    from tools.ui_automation import do_click_element, do_find_element

    acted = False
    for name in DISMISS_NAMES:
        found = do_find_element(name=name, role="Button", window_title=window_title)
        if not found.get("found"):
            found = do_find_element(name=name, window_title=window_title)
        if found.get("found"):
            do_click_element(name=name, window_title=window_title, remember=False)
            acted = True
            time.sleep(0.25)
    return acted


def attempt_recovery(ctx: dict, *, max_attempts: int = 3) -> bool:
    import os

    if not os.environ.get("AWDUI_AUTO_RECOVERY"):
        return False
    from tests.integration.evidence import capture_evidence

    window_title = ctx.get("window_title") or ""
    ticket_id = ctx.get("ticket_id") or "recovery"

    for attempt in range(max_attempts):
        capture_evidence(f"blocked_{ticket_id}_a{attempt}", window_title or "desktop")

        blockers = detect_blockers(window_title)
        if blockers:
            for b in blockers:
                foreign = b.get("title") or ""
                if foreign:
                    from tools.windows import do_focus_window
                    do_focus_window(foreign, action="focus")
                    _try_dismiss_dialogs(foreign)

        from tools.input_tools import do_send_keys
        do_send_keys("escape")
        time.sleep(0.2)

        if window_title:
            from tools.windows import do_focus_window
            do_focus_window(window_title, action="focus")
            _try_dismiss_dialogs(window_title)

        try:
            from tools.screenshot import wait_for_change
            wait_for_change(timeout=2.0, threshold=0.005)
        except Exception:
            pass

        if not detect_blockers(window_title):
            return True
        time.sleep(0.4)

    capture_evidence(f"blocked_{ticket_id}_final", window_title or "desktop")
    return False


def with_step_recovery(
    fn: Callable[[], Any],
    *,
    ctx: Optional[dict] = None,
    timeout_s: float = 45.0,
    max_recovery: int = 2,
) -> Any:
    """Run fn; on failure/timeout attempt recovery and retry."""
    ctx = ctx or {}
    deadline = time.time() + timeout_s
    last_exc: Optional[Exception] = None

    for attempt in range(max_recovery + 1):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if time.time() >= deadline:
                break
            if attempt >= max_recovery:
                break
            attempt_recovery(ctx, max_attempts=2)
            time.sleep(0.5)

    if last_exc:
        raise last_exc
    raise RuntimeError("with_step_recovery failed without exception")

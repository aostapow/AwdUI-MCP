"""Resolve automation window scope (target + modal / MDI children)."""
from __future__ import annotations

from typing import Any, Optional

_DIALOG_CLASSES = frozenset({"#32770"})


def list_owned_dialogs(
    parent_pid: Optional[int] = None,
    dialog_class: str = "#32770",
) -> list[dict[str, Any]]:
    """Return visible dialog windows, optionally filtered by owning process."""
    import sys

    if sys.platform != "win32":
        return []

    from tools.windows import do_list_windows

    cls_want = (dialog_class or "#32770").strip()
    out: list[dict[str, Any]] = []
    for win in do_list_windows():
        cls = (win.get("class_name") or "").strip()
        if cls != cls_want:
            continue
        if parent_pid is not None:
            win_pid = win.get("pid") or win.get("process_id")
            try:
                if int(win_pid) != int(parent_pid):
                    continue
            except (TypeError, ValueError):
                continue
        out.append(win)
    return out


def modal_title_visible(
    modal_title: str,
    parent_pid: Optional[int] = None,
) -> bool:
    """True if a dialog whose title contains *modal_title* is still visible."""
    needle = (modal_title or "").strip().lower()
    if not needle:
        return False
    for win in list_owned_dialogs(parent_pid=parent_pid):
        title = (win.get("title") or "").lower()
        if needle in title:
            return True
    return False


def _window_pid(win: dict) -> Optional[int]:
    pid = win.get("pid") or win.get("process_id")
    try:
        return int(pid) if pid is not None else None
    except (TypeError, ValueError):
        return None


def resolve_foreground_owned_modal(
    parent_pid: Optional[int] = None,
    parent_hwnd: Optional[int] = None,
) -> Optional[dict[str, Any]]:
    """Return foreground #32770 dialog owned by *parent_pid* (same process)."""
    import sys

    if sys.platform != "win32":
        return None

    from awdui_platform.win32_backend import get_foreground_hwnd
    from tools.windows import do_list_windows

    fg_hwnd = int(get_foreground_hwnd() or 0)
    if not fg_hwnd:
        return None
    if parent_hwnd is not None and fg_hwnd == int(parent_hwnd):
        return None

    fg_win = next(
        (w for w in do_list_windows() if int(w.get("hwnd") or 0) == fg_hwnd),
        None,
    )
    if not fg_win:
        return None

    cls = (fg_win.get("class_name") or "").strip()
    if cls not in _DIALOG_CLASSES:
        return None

    fg_pid = _window_pid(fg_win)
    if parent_pid is not None and fg_pid != parent_pid:
        return None

    return {
        "title": fg_win.get("title") or "",
        "hwnd": fg_hwnd,
        "class_name": cls,
        "pid": fg_pid,
    }


def resolve_form_read_scope(
    window_title: Optional[str] = None,
    window_handle: Optional[int] = None,
    scope_mode: str = "auto",
) -> dict[str, Any]:
    """Resolve window title/HWND for form read/fill with optional modal auto-scope."""
    from tools.params import resolve_scoped_window

    mode = (scope_mode or "auto").strip().lower()
    wt, hwnd, _err = resolve_scoped_window("", window_title or "", "", window_handle or 0)

    base: dict[str, Any] = {
        "scope": "target",
        "window_title": wt,
        "window_handle": hwnd,
    }

    if mode == "target" or (window_handle and mode != "foreground"):
        return base

    if mode == "foreground":
        modal = resolve_foreground_owned_modal()
        if modal:
            return {
                **base,
                "scope": "foreground",
                "window_title": modal["title"],
                "window_handle": modal["hwnd"],
                "modal_class": modal.get("class_name"),
            }
        return base

    # auto — prefer foreground owned modal over parent when caller did not pin HWND
    if window_handle:
        return base

    scope = resolve_window_scope(wt)
    parent = scope.get("window") or {}
    parent_pid = _window_pid(parent)
    parent_hwnd = parent.get("hwnd")
    modal = resolve_foreground_owned_modal(
        parent_pid=parent_pid,
        parent_hwnd=int(parent_hwnd) if parent_hwnd else None,
    )
    if not modal:
        # WebView2/Edge file pickers (e.g. Teams attach) may use msedgewebview2.exe PID.
        modal = resolve_foreground_owned_modal(
            parent_pid=None,
            parent_hwnd=int(parent_hwnd) if parent_hwnd else None,
        )
    if modal:
        return {
            "scope": "foreground_modal",
            "window_title": modal["title"],
            "window_handle": modal["hwnd"],
            "modal_class": modal.get("class_name"),
            "parent_title": wt,
        }
    return base


def resolve_action_scope(
    window_title: Optional[str] = None,
    window_handle: Optional[int] = None,
    scope_mode: str = "auto",
) -> dict[str, Any]:
    """Resolve click/invoke scope; ``auto`` prefers foreground #32770 owned by target PID."""
    return resolve_form_read_scope(
        window_title=window_title,
        window_handle=window_handle,
        scope_mode=scope_mode,
    )


def resolve_window_scope(window_title: Optional[str] = None) -> dict[str, Any]:
    from tools.target_window import get_target
    from tools.windows import do_list_windows, find_matching_window

    requested = (window_title or "").strip()
    title = requested or (get_target() or "").strip()
    windows = do_list_windows()

    if not title:
        return {
            "requested_title": requested,
            "resolved_title": "",
            "has_target": False,
            "scoped": "none",
            "window": None,
        }

    direct = find_matching_window(title, windows)
    if direct.get("window"):
        return {
            "requested_title": requested,
            "resolved_title": title,
            "has_target": True,
            "scoped": "direct",
            "window": direct["window"],
            "match_quality": direct.get("match_quality", "exact"),
        }

    target = (get_target() or "").strip()
    parent = None
    parent_title = ""
    parent_pid = None
    if target:
        parent_match = find_matching_window(target, windows)
        parent = parent_match.get("window")
        if parent:
            parent_title = parent.get("title") or target
            parent_pid = parent.get("process_id")

    title_lower = title.lower()
    for win in windows:
        win_title = win.get("title") or ""
        if title_lower not in win_title.lower():
            continue
        if parent_pid is not None and win.get("process_id") == parent_pid:
            return {
                "requested_title": requested,
                "resolved_title": title,
                "has_target": True,
                "scoped": "mdi_child",
                "window": win,
                "parent_title": parent_title,
            }

    return {
        "requested_title": requested,
        "resolved_title": title,
        "has_target": bool(target or requested),
        "scoped": "not_found",
        "window": None,
        "available": direct.get("available", []),
    }

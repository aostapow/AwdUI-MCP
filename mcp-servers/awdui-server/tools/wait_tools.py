"""UIA wait layer — poll for elements and property conditions (semantic verify).

Prefer over wait_for_change (pixel diff) for post-action verification.
"""
from __future__ import annotations

import sys
import time
from typing import Any, Optional

_BOOL_TRUE = frozenset({"true", "1", "on", "yes"})
_BOOL_FALSE = frozenset({"false", "0", "off", "no"})


def _norm_prop_key(name: str) -> str:
    return (name or "").strip().lower().replace("_", "").replace(" ", "")


def _norm_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _boolish(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    text = _norm_text(value)
    if text in _BOOL_TRUE:
        return "true"
    if text in _BOOL_FALSE:
        return "false"
    return text


def _read_properties(
    name: Optional[str] = None,
    automation_id: Optional[str] = None,
    role: Optional[str] = None,
    window_title: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Read live element properties (spy sidecar when available, else UIA)."""
    if sys.platform == "darwin":
        from tools.ui_automation import do_get_element_properties

        result = do_get_element_properties(
            name=name,
            automation_id=automation_id,
            window_title=window_title,
        )
        if not result.get("found"):
            return None
        return result.get("properties") or {}

    if automation_id or name:
        try:
            from tools.spy_bridge import _sidecar_exe, spy_inspect_element

            if _sidecar_exe():
                hit = spy_inspect_element(
                    name=name,
                    automation_id=automation_id,
                    window_title=window_title,
                )
                if hit.get("found"):
                    return hit.get("properties") or {}
        except Exception:
            pass

    from tools.ui_automation import do_find_element, do_get_element_properties

    if automation_id or name:
        result = do_get_element_properties(
            name=name,
            automation_id=automation_id,
            window_title=window_title,
        )
        if result.get("found"):
            return result.get("properties") or {}

    if role:
        found = do_find_element(
            name=name,
            role=role,
            automation_id=automation_id,
            window_title=window_title,
            remember=False,
        )
        if found.get("found") and found.get("elements"):
            return found["elements"][0]

    return None


def _extract_property(props: dict[str, Any], property_name: str) -> str:
    key = _norm_prop_key(property_name)
    patterns = props.get("patterns") or {}

    if key == "name":
        return str(props.get("name") or "")

    if key in ("isenabled", "enabled"):
        if "is_enabled" in props:
            return _boolish(props.get("is_enabled"))
        return _boolish(props.get("enabled", True))

    if key in ("isoffscreen", "offscreen"):
        if "is_offscreen" in props:
            return _boolish(props.get("is_offscreen"))
        visible = props.get("visible")
        if visible is not None:
            return "true" if not bool(visible) else "false"
        return "false"

    if key in ("visible", "isonscreen"):
        if "is_offscreen" in props:
            return "false" if bool(props.get("is_offscreen")) else "true"
        return _boolish(props.get("visible", True))

    if key in ("text", "value"):
        val_pat = patterns.get("Value")
        if isinstance(val_pat, dict) and val_pat.get("value") is not None:
            return str(val_pat.get("value") or "")
        return str(props.get("value") or props.get("name") or "")

    if key in ("ischecked", "checked"):
        toggle = patterns.get("Toggle")
        if isinstance(toggle, dict) and toggle.get("state") is not None:
            state = _norm_text(toggle.get("state"))
            if state in ("on", "indeterminate"):
                return "true"
            if state == "off":
                return "false"
            return state
        return ""

    if key in ("isselected", "selected"):
        sel = patterns.get("SelectionItem")
        if isinstance(sel, dict) and "is_selected" in sel:
            return _boolish(sel.get("is_selected"))
        return ""

    if key in ("selecteditem",):
        return str(props.get("value") or props.get("name") or "")

    if key in ("role", "controltype"):
        role = str(props.get("role") or "")
        return role.replace("ControlType.", "")

    # Generic fallback
    if key in props:
        return str(props.get(key) or "")
    return ""


def _property_matches(actual: str, expected: str, property_name: str) -> bool:
    if expected == "":
        return bool(actual.strip())
    key = _norm_prop_key(property_name)
    actual_n = _norm_text(actual)
    expected_n = _norm_text(expected)

    if key in (
        "isenabled",
        "enabled",
        "isoffscreen",
        "offscreen",
        "visible",
        "isonscreen",
        "ischecked",
        "checked",
        "isselected",
        "selected",
    ):
        return _boolish(actual) == _boolish(expected)

    return expected_n in actual_n or actual_n == expected_n


def do_wait_for_element(
    automation_id: Optional[str] = None,
    name: Optional[str] = None,
    role: Optional[str] = None,
    window_title: Optional[str] = None,
    timeout_ms: int = 10000,
    poll_ms: int = 100,
) -> dict[str, Any]:
    """Poll until an element appears in the UIA tree."""
    from tools.ui_automation import do_find_element

    if not (automation_id or name or role):
        return {"success": False, "error": "automation_id, name, or role required"}

    timeout_s = max(timeout_ms, 0) / 1000.0
    poll_s = max(poll_ms, 10) / 1000.0
    start = time.monotonic()
    attempts = 0
    last_error = ""

    while True:
        attempts += 1
        found = do_find_element(
            name=name,
            role=role,
            automation_id=automation_id,
            window_title=window_title,
            remember=False,
        )
        if found.get("found") and found.get("elements"):
            elapsed_ms = int((time.monotonic() - start) * 1000)
            element = found["elements"][0]
            return {
                "success": True,
                "elapsed_ms": elapsed_ms,
                "attempts": attempts,
                "element": element,
                "backend_used": found.get("backend_used", ""),
            }

        last_error = found.get("error") or "not found"
        elapsed = time.monotonic() - start
        if elapsed >= timeout_s:
            return {
                "success": False,
                "elapsed_ms": int(elapsed * 1000),
                "attempts": attempts,
                "error": last_error or "timeout",
                "code": "timeout",
            }
        time.sleep(poll_s)


def do_wait_for_condition(
    property: str,
    expected_value: str,
    automation_id: Optional[str] = None,
    name: Optional[str] = None,
    role: Optional[str] = None,
    window_title: Optional[str] = None,
    timeout_ms: int = 10000,
    poll_ms: int = 100,
) -> dict[str, Any]:
    """Poll until an element property matches expected_value (case-insensitive)."""
    if not property:
        return {"success": False, "error": "property required"}
    if not (automation_id or name):
        return {"success": False, "error": "automation_id or name required"}

    timeout_s = max(timeout_ms, 0) / 1000.0
    poll_s = max(poll_ms, 10) / 1000.0
    start = time.monotonic()
    attempts = 0
    last_actual = ""

    while True:
        attempts += 1
        props = _read_properties(
            name=name,
            automation_id=automation_id,
            role=role,
            window_title=window_title,
        )
        if props:
            last_actual = _extract_property(props, property)
            if _property_matches(last_actual, expected_value, property):
                elapsed_ms = int((time.monotonic() - start) * 1000)
                return {
                    "success": True,
                    "elapsed_ms": elapsed_ms,
                    "attempts": attempts,
                    "property": property,
                    "expected": expected_value,
                    "actual": last_actual,
                    "element": {
                        "name": props.get("name", ""),
                        "role": props.get("role", ""),
                        "automation_id": props.get("automation_id", ""),
                    },
                }

        elapsed = time.monotonic() - start
        if elapsed >= timeout_s:
            return {
                "success": False,
                "elapsed_ms": int(elapsed * 1000),
                "attempts": attempts,
                "property": property,
                "expected": expected_value,
                "actual": last_actual,
                "error": "timeout",
                "code": "timeout",
            }
        time.sleep(poll_s)


def do_element_exists(
    automation_id: Optional[str] = None,
    name: Optional[str] = None,
    role: Optional[str] = None,
    window_title: Optional[str] = None,
) -> bool:
    """Single-shot presence check (no polling)."""
    from tools.ui_automation import do_find_element

    found = do_find_element(
        name=name,
        role=role,
        automation_id=automation_id,
        window_title=window_title,
        remember=False,
    )
    return bool(found.get("found") and found.get("elements"))


def do_wait_for_input_idle(
    window_title: Optional[str] = None,
    timeout_ms: int = 10000,
) -> dict[str, Any]:
    """Wait until the target window process is ready for input (Windows)."""
    if sys.platform != "win32":
        return {"success": False, "error": "wait_for_input_idle is Windows-only"}

    import ctypes
    import ctypes.wintypes

    from tools.target_window import get_target
    from tools.windows import resolve_window_handle

    title = (window_title or get_target() or "").strip()
    if not title:
        return {"success": False, "error": "window_title required (or set_target_window)"}

    hwnd = resolve_window_handle(title)
    if not hwnd:
        return {"success": False, "error": f"window not found: {title}"}

    pid = ctypes.wintypes.DWORD()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return {"success": False, "error": "cannot resolve process id"}

    PROCESS_QUERY_INFORMATION = 0x0400
    SYNCHRONIZE = 0x00100000
    h_process = ctypes.windll.kernel32.OpenProcess(
        PROCESS_QUERY_INFORMATION | SYNCHRONIZE,
        False,
        pid.value,
    )
    if not h_process:
        return {"success": False, "error": "cannot open process handle"}

    start = time.monotonic()
    try:
        result = ctypes.windll.user32.WaitForInputIdle(h_process, int(timeout_ms))
    finally:
        ctypes.windll.kernel32.CloseHandle(h_process)

    elapsed_ms = int((time.monotonic() - start) * 1000)
    WAIT_TIMEOUT = 0x102
    if result == 0:
        return {"success": True, "elapsed_ms": elapsed_ms, "window_title": title, "pid": pid.value}
    if result == WAIT_TIMEOUT:
        return {
            "success": False,
            "elapsed_ms": elapsed_ms,
            "error": "timeout",
            "code": "timeout",
            "window_title": title,
            "pid": pid.value,
        }
    return {
        "success": False,
        "elapsed_ms": elapsed_ms,
        "error": f"WaitForInputIdle failed (code={result})",
        "window_title": title,
        "pid": pid.value,
    }


def do_invalidate_uia_cache(
    window_title: Optional[str] = None,
    hwnd: Optional[int] = None,
) -> dict[str, Any]:
    """Clear UIA/list caches after relaunch, mode switch, or stale reads."""
    from detection.orchestrator import invalidate_tree_cache
    from detection.uia_tree_cache import invalidate, invalidate_all
    from tools.window_classify import invalidate_cache as invalidate_classify_cache

    details: dict[str, Any] = {}
    details["list_elements_cache"] = invalidate_tree_cache(window_title or None)
    invalidate_classify_cache()
    details["window_classify"] = True

    if hwnd is not None and int(hwnd) > 0:
        invalidate(int(hwnd))
        details["uia_descendants"] = 1
        return {
            "success": True,
            "invalidated": "hwnd",
            "hwnd": int(hwnd),
            "window_title": window_title or "",
            "details": details,
        }

    details["uia_descendants"] = invalidate_all()
    return {
        "success": True,
        "invalidated": "all",
        "window_title": window_title or "",
        "details": details,
    }


def register(server) -> int:
    """Register wait tools on *server*."""
    from tools.params import resolve_window_title as _wt
    from tools.safety import ActionTimeoutError, with_timeout

    @server.tool()
    def wait_for_element(
        automation_id: str = "",
        name: str = "",
        role: str = "",
        window_title: str = "",
        title: str = "",
        timeout_ms: int = 10000,
        poll_ms: int = 100,
    ) -> str:
        """Wait until a UI element appears (UIA poll). Use after navigation or dialog open.

        Prefer this over wait_for_change when you know the control id or name.
        """
        try:
            result = with_timeout(
                lambda: do_wait_for_element(
                    automation_id=automation_id or None,
                    name=name or None,
                    role=role or None,
                    window_title=_wt(window_title, title),
                    timeout_ms=timeout_ms,
                    poll_ms=poll_ms,
                ),
                timeout=max(timeout_ms / 1000.0, 1.0) + 5.0,
            )
        except ActionTimeoutError as exc:
            return f"ERROR: {exc}"

        if result.get("success"):
            elem = result.get("element") or {}
            label = elem.get("automation_id") or elem.get("name") or role or "element"
            return (
                f"OK found {label} after {result.get('elapsed_ms', 0)}ms "
                f"({result.get('attempts', 0)} polls)"
            )
        return (
            f"TIMEOUT after {result.get('elapsed_ms', 0)}ms "
            f"({result.get('attempts', 0)} polls): {result.get('error', 'not found')}"
        )

    @server.tool()
    def wait_for_condition(
        property: str,
        expected_value: str,
        automation_id: str = "",
        name: str = "",
        role: str = "",
        window_title: str = "",
        title: str = "",
        timeout_ms: int = 10000,
        poll_ms: int = 100,
    ) -> str:
        """Wait until an element property reaches expected_value (semantic verify).

        Properties: name, isEnabled, isOffscreen, visible, text, value, isChecked,
        isSelected, selectedItem. Comparison is case-insensitive; text/value use contains.
        """
        try:
            result = with_timeout(
                lambda: do_wait_for_condition(
                    property=property,
                    expected_value=expected_value,
                    automation_id=automation_id or None,
                    name=name or None,
                    role=role or None,
                    window_title=_wt(window_title, title),
                    timeout_ms=timeout_ms,
                    poll_ms=poll_ms,
                ),
                timeout=max(timeout_ms / 1000.0, 1.0) + 5.0,
            )
        except ActionTimeoutError as exc:
            return f"ERROR: {exc}"

        if result.get("success"):
            return (
                f"OK {property}='{result.get('actual')}' "
                f"(expected '{expected_value}') after {result.get('elapsed_ms', 0)}ms"
            )
        return (
            f"TIMEOUT {property}: actual='{result.get('actual', '')}' "
            f"expected='{expected_value}' after {result.get('elapsed_ms', 0)}ms"
        )

    @server.tool()
    def wait_for_input_idle(
        window_title: str = "",
        title: str = "",
        timeout_ms: int = 10000,
    ) -> str:
        """Wait until the target window is idle and ready for input (Windows).

        Use after launch_app or heavy navigation before the first interaction.
        """
        try:
            result = with_timeout(
                lambda: do_wait_for_input_idle(
                    window_title=_wt(window_title, title) or None,
                    timeout_ms=timeout_ms,
                ),
                timeout=max(timeout_ms / 1000.0, 1.0) + 5.0,
            )
        except ActionTimeoutError as exc:
            return f"ERROR: {exc}"

        if result.get("success"):
            return (
                f"OK idle after {result.get('elapsed_ms', 0)}ms "
                f"(pid={result.get('pid')}, window='{result.get('window_title', '')}')"
            )
        return f"FAIL: {result.get('error', 'unknown')} ({result.get('elapsed_ms', 0)}ms)"

    @server.tool()
    def element_exists(
        automation_id: str = "",
        name: str = "",
        role: str = "",
        window_title: str = "",
        title: str = "",
    ) -> str:
        """Single-shot check whether a control exists (no polling).

        Use before acting on optional UI; prefer wait_for_element when you can wait.
        """
        exists = do_element_exists(
            automation_id=automation_id or None,
            name=name or None,
            role=role or None,
            window_title=_wt(window_title, title),
        )
        label = automation_id or name or role or "element"
        return f"OK exists {label}" if exists else f"NOT FOUND {label}"

    @server.tool()
    def invalidate_cache(
        window_title: str = "",
        title: str = "",
        hwnd: int = 0,
    ) -> str:
        """Clear UIA caches after relaunch, Calculator mode switch, or stale element reads.

        Clears list_elements tree cache, per-HWND descendant cache, and window classify cache.
        Pass hwnd to scope descendant cache to one window; omit for full invalidation.
        """
        result = do_invalidate_uia_cache(
            window_title=_wt(window_title, title) or None,
            hwnd=int(hwnd) if hwnd and int(hwnd) > 0 else None,
        )
        if not result.get("success"):
            return result.get("error", "invalidate_cache failed")
        invalidated = result.get("invalidated", "all")
        details = result.get("details") or {}
        if invalidated == "hwnd":
            return (
                f"OK invalidated=hwnd hwnd={result.get('hwnd')} "
                f"list_elements_cache={details.get('list_elements_cache', 0)}"
            )
        return (
            f"OK invalidated=all list_elements_cache={details.get('list_elements_cache', 0)} "
            f"uia_descendants={details.get('uia_descendants', 0)}"
        )

    return 5

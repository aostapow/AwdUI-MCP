"""Shared harness for Windows Calculator integration tests."""
from __future__ import annotations

import re
import sys
import time
from typing import Optional

WINDOW_HINTS = ("Calculadora", "Calculator")
PROCESS_NAMES = ("CalculatorApp.exe", "ApplicationFrameHost")

_IDS = {
    "clear": "clearButton",
    "clear_entry": "clearEntryButton",
    "backspace": "backSpaceButton",
    "equals": "equalButton",
    "multiply": "multiplyButton",
    "plus": "plusButton",
    "divide": "divideButton",
    "minus": "minusButton",
    "percent": "percentButton",
    "sqrt": "squareRootButton",
    "square": "xpower2Button",
    "reciprocal": "invertButton",
    "negate": "negateButton",
    "decimal": "decimalSeparatorButton",
}

# Backward-compatible alias
IDS = _IDS

DISPLAY_AUTOMATION_IDS = (
    "CalculatorResults",
    "Display is",
    "Expression is",
    "CalculatorExpression",
)

_NUMERIC_RE = re.compile(r"[-+]?\d[\d,.\s]*")


def resolve_window_title() -> str:
    from tools.windows import do_list_windows

    windows = do_list_windows()
    # Prefer UWP CoreWindow over ApplicationFrameHost shell (duplicate title).
    for win in windows:
        proc = (win.get("process_name") or "").lower()
        title = (win.get("title") or "").strip()
        if "calculatorapp" in proc and title:
            return title
    for hint in WINDOW_HINTS:
        hint_lower = hint.lower()
        for win in windows:
            title = (win.get("title") or "").strip()
            proc = (win.get("process_name") or "").lower()
            if hint_lower in title.lower() and "applicationframehost" not in proc:
                return title
    for hint in WINDOW_HINTS:
        hint_lower = hint.lower()
        for win in windows:
            title = (win.get("title") or "").strip()
            if hint_lower in title.lower():
                return title
    return ""


def _maybe_begin_gui_session(window_title: str) -> None:
    import os

    if not os.environ.get("AWDUI_GUI_SESSION") and not os.environ.get("PYTEST_CURRENT_TEST"):
        return
    from tests.integration.gui_session import begin

    begin(name="calculator_harness", window_title=window_title, max_clicks=120, max_seconds=600)


def ensure_calculator_running(timeout_s: float = 20.0) -> dict:
    """Launch Calculator, focus, and wait until keypad is visible."""
    if sys.platform != "win32":
        return {"success": False, "error": "Windows only"}

    from tools.windows import do_focus_window, do_launch_app, do_list_windows
    from tools.ui_automation import do_find_element

    title = resolve_window_title()
    if not title:
        launch = do_launch_app("calc.exe")
        if not launch.get("success"):
            return {"success": False, "error": launch.get("error", "launch failed")}
        time.sleep(1.5)

    deadline = time.time() + timeout_s
    title = ""
    while time.time() < deadline:
        title = resolve_window_title()
        if title:
            do_focus_window(title, action="focus")
            found = do_find_element(automation_id="num1Button", window_title=title)
            if found.get("found"):
                set_calc_target(title)
                _maybe_begin_gui_session(title)
                return {"success": True, "window_title": title}
        time.sleep(0.4)

    available = [w.get("title", "") for w in do_list_windows()[:15]]
    return {
        "success": False,
        "error": "Calculator keypad not visible in time",
        "available": available,
    }


def set_calc_target(title: Optional[str] = None) -> str:
    from tools.target_window import set_target

    wt = title or resolve_window_title()
    if wt:
        set_target(wt)
    return wt


def clear_calc_target() -> None:
    from tools.target_window import set_target

    set_target("")


def click_button(
    *,
    automation_id: str = "",
    name: str = "",
    window_title: Optional[str] = None,
    role: Optional[str] = None,
) -> dict:
    from tools.ui_automation import do_click_element

    wt = window_title or resolve_window_title()
    return do_click_element(
        automation_id=automation_id or None,
        name=name or None,
        role=role or None,
        window_title=wt,
        remember=False,
    )


def click_list_item(
    automation_id: str,
    *,
    window_title: Optional[str] = None,
) -> dict:
    """ListItem in NavView — always coordinate click (Invoke fails on UWP)."""
    from tools.ui_automation import do_find_element

    wt = window_title or resolve_window_title()
    found = do_find_element(
        automation_id=automation_id,
        role="ListItem",
        window_title=wt,
        include_offscreen=True,
        remember=False,
    )
    if not found.get("found"):
        return {"success": False, "error": f"ListItem {automation_id} not found"}

    elem = found["elements"][0]
    x = int(elem.get("x", 0)) + int(elem.get("width", 0)) // 2
    y = int(elem.get("y", 0)) + int(elem.get("height", 0)) // 2
    from tests.integration.gui_session import guarded_click

    guarded_click(x, y, window_title=wt, reason=f"list_item:{automation_id}")
    time.sleep(0.5)
    return {"success": True, "method": "coordinate_click", "clicked_at": {"x": x, "y": y}, "element": elem}


def _nav_scroll(x: int, y: int, direction: str = "down", amount: int = 4) -> None:
    from tools.input_tools import do_scroll
    do_scroll(x, y, direction, amount=amount)
    time.sleep(0.2)


def _nav_is_open(window_title: str) -> bool:
    from tools.ui_automation import do_find_element
    nav = do_find_element(automation_id="TogglePaneButton", window_title=window_title)
    if not nav.get("found"):
        return False
    label = (nav["elements"][0].get("name") or "").lower()
    return "cerrar" in label or "close" in label


def open_navigation(window_title: Optional[str] = None) -> dict:
    wt = window_title or resolve_window_title()
    if _nav_is_open(wt):
        return {"success": True, "method": "nav_already_open"}
    return click_button(automation_id="TogglePaneButton", window_title=wt)


def close_navigation(window_title: Optional[str] = None) -> dict:
    wt = window_title or resolve_window_title()
    if not _nav_is_open(wt):
        return {"success": True, "method": "nav_already_closed"}
    return click_button(automation_id="TogglePaneButton", window_title=wt)


def _find_nav_item(automation_id: str, window_title: str) -> Optional[dict]:
    from tools.ui_automation import do_find_element
    found = do_find_element(
        automation_id=automation_id,
        role="ListItem",
        window_title=window_title,
        include_offscreen=True,
        remember=False,
    )
    if not found.get("found"):
        return None
    return found["elements"][0]


def scroll_nav_to_item(automation_id: str, window_title: Optional[str] = None) -> dict:
    """Scroll NavView until ListItem is in visible band (~400-900 y)."""
    wt = window_title or resolve_window_title()
    open_navigation(wt)
    nav_x, nav_y = 267, 550
    _nav_scroll(nav_x, nav_y, "up", amount=12)
    time.sleep(0.3)

    for i in range(16):
        elem = _find_nav_item(automation_id, wt)
        if elem:
            y = int(elem.get("y", 0))
            h = int(elem.get("height", 0))
            cy = y + h // 2
            if 380 <= cy <= 920:
                return {"success": True, "element": elem, "scroll_steps": i}
            if cy > 920:
                _nav_scroll(nav_x, nav_y, "down", amount=3)
            else:
                _nav_scroll(nav_x, nav_y, "up", amount=3)
        else:
            _nav_scroll(nav_x, nav_y, "down", amount=3)
        time.sleep(0.25)

    elem = _find_nav_item(automation_id, wt)
    if elem:
        return {"success": True, "element": elem, "scroll_steps": 16, "note": "best_effort"}
    return {"success": False, "error": f"could not scroll to {automation_id}"}


MODE_HEADER_HINTS = {
    "Standard": ("estándar", "standard"),
    "Scientific": ("científica", "scientific"),
    "Graphing": ("graficar", "graphing"),
    "Programmer": ("programador", "programmer"),
    "Date": ("fecha", "date"),
    "Currency": ("divisa", "currency"),
    "Volume": ("volumen", "volume"),
    "Length": ("longitud", "length"),
    "SettingsItem": ("configuración", "settings"),
}


def switch_mode(mode_id: str, window_title: Optional[str] = None, retries: int = 3) -> dict:
    """Switch calculator mode via NavView ListItem."""
    wt = window_title or resolve_window_title()
    hints = MODE_HEADER_HINTS.get(mode_id, (mode_id.lower(),))

    for attempt in range(retries + 1):
        scrolled = scroll_nav_to_item(mode_id, window_title=wt)
        if not scrolled.get("success"):
            time.sleep(0.3)
            continue
        elem = scrolled["element"]
        x = int(elem.get("x", 0)) + int(elem.get("width", 0)) // 2
        y = int(elem.get("y", 0)) + int(elem.get("height", 0)) // 2
        from tests.integration.gui_session import guarded_click

        guarded_click(x, y, window_title=wt, reason=f"switch_mode:{mode_id}")
        time.sleep(0.8)
        header = get_current_mode(wt).lower()
        if any(h in header for h in hints):
            close_navigation(wt)
            return {"success": True, "header": header, "attempt": attempt}
        close_navigation(wt)
        time.sleep(0.3)

    return {
        "success": False,
        "error": f"mode {mode_id} not active after {retries + 1} tries",
        "header": get_current_mode(wt),
    }


def get_current_mode(window_title: Optional[str] = None) -> str:
    from tools.ui_automation import do_find_element

    wt = window_title or resolve_window_title()
    found = do_find_element(automation_id="Header", window_title=wt)
    if not found.get("found"):
        return ""
    return str(found["elements"][0].get("name") or "")


def inventory_all_elements(window_title: Optional[str] = None, max_depth: int = 10) -> dict:
    """Full UIA inventory grouped by role — not just buttons."""
    from tools.ui_automation import do_list_elements

    wt = window_title or resolve_window_title()
    result = do_list_elements(window_title=wt, max_depth=max_depth)
    by_role: dict[str, list] = {}
    skip_roles = {"Window", "Pane"}
    for e in result.get("elements", []):
        role = e.get("role") or "Unknown"
        aid = (e.get("automation_id") or "").strip()
        name = (e.get("name") or "").strip()
        if role in skip_roles and not aid and not name:
            continue
        entry = {
            "automation_id": aid,
            "name": name,
            "role": role,
            "class_name": e.get("class_name", ""),
        }
        by_role.setdefault(role, []).append(entry)
    return {
        "total": result.get("count", 0),
        "by_role": by_role,
        "roles": sorted(by_role.keys()),
    }


def inventory_buttons(window_title: Optional[str] = None, max_depth: int = 8) -> list[dict]:
    from tests.integration.calculator_map import CHROME
    from tools.ui_automation import do_list_elements

    wt = window_title or resolve_window_title()
    result = do_list_elements(window_title=wt, max_depth=max_depth, role="Button")
    skip = set(CHROME.values()) | {"Minimize", "Maximize", "Close", "LightDismiss"}
    buttons = []
    for e in result.get("elements", []):
        aid = e.get("automation_id") or ""
        if aid in skip:
            continue
        buttons.append({
            "automation_id": aid,
            "name": e.get("name", ""),
            "role": e.get("role", ""),
        })
    return buttons


_DISPLAY_PREFIXES = (
    "se muestra",
    "display is",
    "expression is",
    "muestra",
)


def _extract_numeric(text: str) -> str:
    if not text:
        return ""
    cleaned = text.replace("\u202f", " ").replace("\xa0", " ")
    lower = cleaned.lower()
    for prefix in _DISPLAY_PREFIXES:
        if prefix in lower:
            idx = lower.index(prefix) + len(prefix)
            cleaned = cleaned[idx:].strip()
            break
    matches = _NUMERIC_RE.findall(cleaned)
    if not matches:
        return ""
    raw = matches[-1].strip()
    return raw.replace(" ", "").replace(",", "")


def read_display_uia(window_title: Optional[str] = None) -> dict:
    """Read calculator display via UIA only."""
    from tools.ui_automation import do_find_element, do_list_elements

    wt = window_title or resolve_window_title()
    if not wt:
        return {"value": "", "source": "none", "raw": ""}

    for aid in DISPLAY_AUTOMATION_IDS:
        found = do_find_element(automation_id=aid, window_title=wt, include_offscreen=True)
        if found.get("found"):
            elem = found["elements"][0]
            for key in ("value", "name"):
                val = _extract_numeric(str(elem.get(key) or ""))
                if val:
                    return {"value": val, "source": "uia", "raw": elem.get(key, ""), "automation_id": aid}

    listed = do_list_elements(window_title=wt, max_depth=5, role="Text")
    for elem in listed.get("elements", []):
        val = _extract_numeric(str(elem.get("value") or elem.get("name") or ""))
        if val:
            return {"value": val, "source": "uia", "raw": elem.get("name", ""), "role": elem.get("role")}

    listed = do_list_elements(window_title=wt, max_depth=5)
    for elem in listed.get("elements", []):
        name = str(elem.get("name") or "")
        lower = name.lower()
        if any(p in lower for p in _DISPLAY_PREFIXES) or "expression is" in lower:
            val = _extract_numeric(name)
            if val:
                return {"value": val, "source": "uia", "raw": name, "role": elem.get("role")}

    return {"value": "", "source": "none", "raw": ""}


def read_display(window_title: Optional[str] = None) -> dict:
    """UIA first; caller should use evidence.read_display_with_fallback for OCR."""
    return read_display_uia(window_title)


def compute_expression(
    steps: list[tuple[str, str]],
    *,
    window_title: Optional[str] = None,
) -> list[dict]:
    """Run button clicks; each step is (label, key_or_automation_id)."""
    from tests.integration.calculator_map import SCIENTIFIC_EXTRA, STANDARD_KEYPAD

    lookup = {**STANDARD_KEYPAD, **SCIENTIFIC_EXTRA}
    results: list[dict] = []
    wt = window_title or resolve_window_title()
    for label, locator in steps:
        if locator.isdigit():
            out = click_button(name=locator, window_title=wt)
        elif locator.endswith("Button"):
            out = click_button(automation_id=locator, window_title=wt)
        elif locator in _IDS:
            out = click_button(automation_id=_IDS[locator], window_title=wt)
        elif locator in lookup:
            out = click_button(automation_id=lookup[locator], window_title=wt)
        else:
            out = click_button(automation_id=locator, window_title=wt)
        out["step_label"] = label
        results.append(out)
        if not out.get("success"):
            break
        time.sleep(0.15)
    return results


def teardown_calculator() -> None:
    if sys.platform != "win32":
        return
    try:
        from tools.input_tools import do_send_keys
        from tools.windows import do_focus_window

        title = resolve_window_title()
        if title:
            do_focus_window(title, action="focus")
            time.sleep(0.2)
            do_send_keys("alt+f4")
            time.sleep(0.3)
            do_send_keys("escape")
    except Exception:
        pass
    clear_calc_target()
    try:
        from tests.integration.gui_session import end
        end()
    except Exception:
        pass

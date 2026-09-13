"""UIA3 detection backend — pywinauto + comtypes direct access."""
from __future__ import annotations

import re
import sys
from typing import Any, Optional

from detection.backends.base import DetectionBackend
from detection.element_model import DetectedElement

# UIA pattern IDs (subset)
_UIA_PATTERNS = {
    10000: "Invoke",
    10001: "Selection",
    10002: "Value",
    10003: "RangeValue",
    10004: "Scroll",
    10005: "ExpandCollapse",
    10010: "SelectionItem",
    10015: "Toggle",
    10017: "ScrollItem",
    10018: "LegacyIAccessible",
    10014: "Text",
}

_iuia = None


def _get_iuia():
    global _iuia
    if _iuia is None:
        from pywinauto.uia_defines import IUIA
        _iuia = IUIA()
    return _iuia


def _get_desktop():
    from pywinauto import Desktop
    return Desktop(backend="uia")


def _get_foreground_window(desktop):
    """Resolve the actual foreground window, not desktop.windows()[0]."""
    if sys.platform != "win32":
        windows = desktop.windows()
        return windows[0] if windows else None
    from awdui_platform.win32_backend import get_foreground_hwnd
    from pywinauto.uia_element_info import UIAElementInfo
    hwnd = get_foreground_hwnd()
    if hwnd:
        try:
            return desktop.window(handle=hwnd)
        except Exception:
            pass
        try:
            info = UIAElementInfo(hwnd)
            from pywinauto.controls.uiawrapper import UIAWrapper
            return UIAWrapper(info)
        except Exception:
            pass
    windows = desktop.windows()
    return windows[0] if windows else None


def _find_window(desktop, window_title: Optional[str]):
    from tools.target_window import get_target
    from tools.windows import find_matching_window, resolve_window_handle

    title = (window_title or get_target() or "").strip()
    if not title:
        return None

    hwnd = resolve_window_handle(title)
    if hwnd:
        try:
            return desktop.window(handle=hwnd)
        except Exception:
            pass

    windows = []
    for win in desktop.windows():
        try:
            windows.append({"_obj": win, "title": win.window_text()})
        except Exception:
            continue
    result = find_matching_window(title, windows)
    return result["window"]["_obj"] if result.get("window") else None


def _safe_get(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def _get_patterns(elem) -> list[str]:
    patterns = []
    try:
        raw = elem.element_info.element
        iuia = _get_iuia().iuia
        for pid, pname in _UIA_PATTERNS.items():
            try:
                if raw.GetCurrentPattern(pid) is not None:
                    patterns.append(pname)
            except Exception:
                continue
    except Exception:
        pass
    return patterns


def _get_clickable_point(elem) -> tuple[Optional[int], Optional[int]]:
    try:
        from ctypes import byref
        from ctypes.wintypes import POINT
        pt = POINT()
        raw = elem.element_info.element
        if raw.GetClickablePoint(byref(pt)) != 0:
            return pt.x, pt.y
    except Exception:
        pass
    return None, None


def _pywinauto_to_element(elem, backend: str = "uia") -> Optional[DetectedElement]:
    try:
        info = elem.element_info
        rect = info.rectangle
        cx, cy = _get_clickable_point(elem)
        runtime_id = ""
        try:
            rid = info.runtime_id
            if rid:
                runtime_id = str(list(rid)) if hasattr(rid, "__iter__") else str(rid)
        except Exception:
            pass

        aria_role = ""
        aria_properties = ""
        try:
            raw = info.element
            aria_role = _safe_get(lambda: raw.CurrentAriaRole, "") or ""
            aria_properties = _safe_get(lambda: raw.CurrentAriaProperties, "") or ""
        except Exception:
            pass

        has_focus = False
        is_kbf = False
        enabled = True
        try:
            raw = info.element
            has_focus = bool(_safe_get(lambda: raw.CurrentHasKeyboardFocus, False))
            is_kbf = bool(_safe_get(lambda: raw.CurrentIsKeyboardFocusable, False))
            enabled = bool(_safe_get(lambda: raw.CurrentIsEnabled, True))
        except Exception:
            pass

        return DetectedElement(
            name=info.name or "",
            role=info.control_type or "",
            x=rect.left,
            y=rect.top,
            width=rect.right - rect.left,
            height=rect.bottom - rect.top,
            value=getattr(info, "rich_text", "") or "",
            backend=backend,
            automation_id=info.automation_id or "",
            class_name=info.class_name or "",
            framework_id=info.framework_id or "",
            runtime_id=runtime_id,
            process_id=info.process_id or 0,
            hwnd=info.handle or 0,
            enabled=enabled,
            visible=bool(info.visible),
            has_focus=has_focus,
            is_keyboard_focusable=is_kbf,
            access_key=_safe_get(lambda: info.element.CurrentAccessKey, "") or "",
            help_text=_safe_get(lambda: info.element.CurrentHelpText, "") or "",
            localized_control_type=_safe_get(
                lambda: info.element.CurrentLocalizedControlType, ""
            ) or "",
            aria_role=aria_role,
            aria_properties=aria_properties,
            clickable_x=cx,
            clickable_y=cy,
            patterns=_get_patterns(elem),
        )
    except Exception:
        return None


def _walk_tree_comtypes(root_element, tree_mode: str = "control", max_depth: int = 100):
    """Walk UIA tree using Raw/Content/Control view walkers."""
    iuia = _get_iuia().iuia
    if tree_mode == "raw":
        walker = iuia.RawViewWalker
    elif tree_mode == "content":
        walker = iuia.ContentViewWalker
    else:
        walker = iuia.ControlViewWalker

    from pywinauto.uia_element_info import UIAElementInfo
    from pywinauto.controls.uiawrapper import UIAWrapper

    results = []

    def walk(elem, depth):
        if depth > max_depth:
            return
        try:
            wrapper = UIAWrapper(UIAElementInfo(elem))
            results.append(wrapper)
        except Exception:
            pass
        try:
            child = walker.GetFirstChildElement(elem)
            while child:
                walk(child, depth + 1)
                child = walker.GetNextSiblingElement(child)
        except Exception:
            pass

    walk(root_element, 0)
    return results


def _element_rect_left(raw_elem) -> int:
    try:
        rect = raw_elem.CurrentBoundingRectangle
        return int(rect.left)
    except Exception:
        return 0


def _element_control_type(raw_elem) -> int:
    try:
        return int(raw_elem.CurrentControlType)
    except Exception:
        return 0


def _walk_treeitems_spatial_pruned(
    root_element,
    max_depth: int,
    *,
    prune_left_abs: int,
) -> list:
    """ControlView walk collecting TreeItem in left column; prune wide-content subtrees."""
    iuia = _get_iuia().iuia
    walker = iuia.ControlViewWalker

    from pywinauto.uia_element_info import UIAElementInfo
    from pywinauto.controls.uiawrapper import UIAWrapper

    results: list = []

    def walk(elem, depth: int) -> None:
        if depth > max_depth:
            return
        left = _element_rect_left(elem)
        if depth >= 1 and left > prune_left_abs:
            return
        if _element_control_type(elem) == _UIA_CONTROL_TREEITEM:
            try:
                results.append(UIAWrapper(UIAElementInfo(elem)))
            except Exception:
                pass
        try:
            child = walker.GetFirstChildElement(elem)
            while child:
                walk(child, depth + 1)
                child = walker.GetNextSiblingElement(child)
        except Exception:
            pass

    walk(root_element, 0)
    return results


def _window_prune_left_abs(window) -> int:
    try:
        rect = window.rectangle()
        width = max(int(rect.width()), 1)
        band = min(_SIDEBAR_TREE_MAX_WIDTH + 80, int(width * _SIDEBAR_PRUNE_WIDTH_RATIO))
        return int(rect.left) + band
    except Exception:
        return _SIDEBAR_TREE_MAX_WIDTH + 80


def _resolve_window(desktop, window_title: Optional[str], window_handle: Optional[int] = None):
    if window_handle and int(window_handle) > 0:
        try:
            return desktop.window(handle=int(window_handle))
        except Exception:
            wrapper = _window_from_hwnd(int(window_handle))
            if wrapper is not None:
                return wrapper
    from tools.target_window import get_target

    title = window_title or get_target()
    if title:
        found = _find_window(desktop, title)
        if found:
            return found
    return _get_foreground_window(desktop)


def _window_from_hwnd(hwnd: int):
    try:
        from pywinauto.uia_element_info import UIAElementInfo
        from pywinauto.controls.uiawrapper import UIAWrapper

        info = UIAElementInfo(hwnd)
        return UIAWrapper(info)
    except Exception:
        return None


def _find_raw_by_automation_id_comtypes(window, automation_id: str):
    """FindFirst by AutomationId — O(subtree index) vs pywinauto child_window walks."""
    if not automation_id:
        return None
    try:
        raw = window.element_info.element
    except Exception:
        return None
    try:
        iuia = _get_iuia().iuia
        condition = iuia.CreatePropertyCondition(
            _UiaAutomationIdPropertyId, automation_id
        )
        elem = raw.FindFirst(_UiaTreeScopeDescendants, condition)
    except Exception:
        return None
    if elem is None:
        return None
    try:
        from pywinauto.controls.uiawrapper import UIAWrapper
        from pywinauto.uia_element_info import UIAElementInfo

        return UIAWrapper(UIAElementInfo(elem))
    except Exception:
        return None


def _find_raw_by_automation_id(window, automation_id: str):
    """Targeted property lookup — avoids full tree walks when automation_id is set."""
    if not automation_id:
        return None
    hit = _find_raw_by_automation_id_comtypes(window, automation_id)
    if hit is not None:
        return hit
    try:
        elem = window.child_window(auto_id=automation_id)
        if elem.exists(timeout=0):
            return elem
    except Exception:
        pass
    return None


def _find_raw_direct(
    window,
    name: Optional[str] = None,
    role: Optional[str] = None,
    automation_id: Optional[str] = None,
):
    """Fast UIA condition search before subtree walks."""
    if automation_id:
        return _find_raw_by_automation_id(window, automation_id)
    needle = (name or "").strip()
    if not needle:
        return None
    kwargs: dict = {}
    if role:
        kwargs["control_type"] = role
    patterns = [needle]
    if len(needle) > 24:
        patterns.append(needle[:24])
    first_token = needle.split()[0] if needle.split() else ""
    if first_token and first_token not in patterns and len(first_token) >= 4:
        patterns.append(first_token)
    for pat in patterns:
        try:
            elem = window.child_window(title_re=f".*{re.escape(pat)}.*", **kwargs)
            if elem.exists(timeout=0):
                return elem
        except Exception:
            continue
    try:
        elem = window.child_window(best_match=needle, **kwargs)
        if elem.exists(timeout=0):
            return elem
    except Exception:
        pass
    return None


_FIND_DEPTH_LADDER = (6, 10, 14, 18, 24)
_FIND_DEPTH_LADDER_AUTOMATION_ID = (4, 8, 14)

_TYPED_ROLE_CONTROL = {
    "treeitem": "TreeItem",
    "listitem": "ListItem",
    "tabitem": "TabItem",
}

# UIA ControlType ids (UIAutomationClient.h) — used for pruned walks only.
_UIA_CONTROL_TREEITEM = 50024
_UiaControlTypePropertyId = 30003
_UiaAutomationIdPropertyId = 30011
_UiaTreeScopeDescendants = 4

# Narrow Tree roots (Electron nav/chat columns) — app-agnostic width band.
_SIDEBAR_TREE_MAX_WIDTH = 520
_SIDEBAR_TREE_MIN_WIDTH = 120
_SIDEBAR_TREE_MIN_ITEMS = 5
_SIDEBAR_TREE_FULL_ITEMS = 35
_SIDEBAR_PRUNE_WIDTH_RATIO = 0.42


def _prefer_uia_find_before_spy(window_title: Optional[str]) -> bool:
    """Electron/Teams: FlaUI sidecar find often 8–15s; try local UIA first."""
    try:
        from tools.framework_detect import do_detect_framework

        fw = do_detect_framework(window_title).get("framework", "")
        return fw in ("electron", "chromium_browser")
    except Exception:
        return False


def _should_skip_spy_list(
    window_title: Optional[str],
    role_lower: Optional[str],
    has_uia_elements: bool,
) -> bool:
    """Skip FlaUI sidecar list when local UIA already satisfied the query."""
    if not has_uia_elements:
        return False
    if role_lower in ("menuitem", "menu"):
        return True
    if role_lower in _TYPED_ROLE_CONTROL:
        return True
    return _prefer_uia_find_before_spy(window_title)


def _element_useful(d: DetectedElement, include_offscreen: bool) -> bool:
    if not include_offscreen and not d.visible:
        return False
    if d.name or d.role not in ("", "Pane", "Group", "Custom"):
        return True
    if d.automation_id or d.class_name:
        return True
    return False


def _matches(
    d: DetectedElement,
    name: Optional[str],
    role: Optional[str],
    automation_id: Optional[str],
    class_name: Optional[str],
) -> bool:
    if name and name.lower() not in (d.name or "").lower():
        return False
    if role and role.lower() != (d.role or "").lower():
        return False
    if automation_id and automation_id != d.automation_id:
        return False
    if class_name and class_name.lower() not in (d.class_name or "").lower():
        return False
    return True


class UIABackend(DetectionBackend):
    name = "uia"

    def is_available(self) -> bool:
        return sys.platform == "win32"

    def _collect_descendants(
        self, window, tree_mode: str, max_depth: int, role: Optional[str]
    ):
        role_lower = (role or "").strip().lower()
        if role_lower in ("menuitem", "menu"):
            return self._collect_menu_elements(window, tree_mode, max_depth)
        if role_lower in _TYPED_ROLE_CONTROL:
            typed = self._collect_typed_role_elements(window, max_depth, role_lower)
            if typed:
                return typed

        comtypes_cap = max_depth
        if role:
            comtypes_cap = min(max(max_depth, max_depth + 2), 24)

        try:
            raw = window.element_info.element
            walked = _walk_tree_comtypes(raw, tree_mode, comtypes_cap)
            if walked:
                return walked
        except Exception:
            pass
        descendant_depth = min(max_depth, 24) if role else max_depth
        try:
            return window.descendants(depth=descendant_depth)
        except Exception:
            return []

    def _collect_menu_elements(self, window, tree_mode: str, max_depth: int):
        """Shallow walk for MenuItem/Menu — avoids full-window depth-100 comtypes walks."""
        cap = min(max(int(max_depth or 4), 4), 8)
        collected: list = []
        seen: set[int] = set()

        def _add_wrappers(wrappers) -> None:
            for wrapper in wrappers or []:
                key = id(getattr(wrapper, "element_info", wrapper))
                if key in seen:
                    continue
                seen.add(key)
                collected.append(wrapper)

        try:
            raw = window.element_info.element
            _add_wrappers(_walk_tree_comtypes(raw, tree_mode, cap))
        except Exception:
            pass

        try:
            menubar = window.child_window(control_type="MenuBar")
            if menubar.exists(timeout=0):
                _add_wrappers(
                    _walk_tree_comtypes(menubar.element_info.element, tree_mode, cap)
                )
        except Exception:
            pass

        if collected:
            return collected

        try:
            return window.descendants(depth=cap)
        except Exception:
            return []

    def _findall_sidebar_treeitems(self, window, prune_left: int) -> list:
        """Single UIA FindAll pass filtered to sidebar column."""
        try:
            raw = window.element_info.element
        except Exception:
            return []
        try:
            iuia = _get_iuia().iuia
            condition = iuia.CreatePropertyCondition(
                _UiaControlTypePropertyId, _UIA_CONTROL_TREEITEM
            )
            arr = raw.FindAll(_UiaTreeScopeDescendants, condition)
        except Exception:
            return []
        if arr is None:
            return []
        try:
            count = int(arr.Length)
        except Exception:
            return []
        from pywinauto.uia_element_info import UIAElementInfo
        from pywinauto.controls.uiawrapper import UIAWrapper

        results: list = []
        for i in range(count):
            try:
                elem = arr.GetElement(i)
            except Exception:
                continue
            if _element_rect_left(elem) > prune_left:
                continue
            try:
                results.append(UIAWrapper(UIAElementInfo(elem)))
            except Exception:
                continue
        return results

    @staticmethod
    def _treeitem_dedupe_key(wrapper) -> str:
        det = _pywinauto_to_element(wrapper)
        if not det:
            return str(id(wrapper))
        return f"{det.automation_id}|{det.name}|{int(det.y or 0)}"

    def _merge_treeitem_wrappers(self, *groups: list) -> list:
        seen: set[str] = set()
        merged: list = []
        for group in groups:
            for wrapper in group or []:
                key = self._treeitem_dedupe_key(wrapper)
                if key in seen:
                    continue
                seen.add(key)
                merged.append(wrapper)
        return merged

    def _resolve_sidebar_scroll_raw(self, merged: list):
        """Pick a scrollable UIA node for the chat sidebar list."""
        from detection.uia_patterns import find_scrollable_ancestor

        for wrapper in merged:
            det = _pywinauto_to_element(wrapper)
            if not det:
                continue
            name = (det.name or "").strip()
            if name == "Chats":
                try:
                    ancestor = find_scrollable_ancestor(
                        wrapper.element_info.element, max_levels=20
                    )
                    return ancestor or wrapper.element_info.element
                except Exception:
                    continue

        chat_wrappers: list[tuple[int, object]] = []
        for wrapper in merged:
            det = _pywinauto_to_element(wrapper)
            if not det:
                continue
            name = (det.name or "").strip()
            if name.startswith("Chat "):
                chat_wrappers.append((int(det.y or 0), wrapper))
        if chat_wrappers:
            chat_wrappers.sort(key=lambda item: item[0])
            bottom = chat_wrappers[-1][1]
            try:
                raw = bottom.element_info.element
                ancestor = find_scrollable_ancestor(raw, max_levels=20)
                return ancestor or raw
            except Exception:
                pass

        if merged:
            try:
                return find_scrollable_ancestor(
                    merged[-1].element_info.element, max_levels=20
                )
            except Exception:
                return None
        return None

    def _scroll_raw_for_sidebar_chat(self, merged: list):
        """Resolve scroll container from bottom visible chat via fresh UIA lookup."""
        from detection.uia_patterns import find_scrollable_ancestor

        chat_aids: list[tuple[int, str]] = []
        for wrapper in merged:
            det = _pywinauto_to_element(wrapper)
            if not det:
                continue
            name = (det.name or "").strip()
            aid = (getattr(det, "automation_id", "") or "").strip()
            if name.startswith("Chat ") and aid:
                chat_aids.append((int(det.y or 0), aid))
        if chat_aids:
            chat_aids.sort(key=lambda item: item[0])
            aid = chat_aids[-1][1]
            try:
                from tools.uia_pattern_tools import _resolve_raw_control

                raw, _data, _resolved, _scope = _resolve_raw_control(
                    automation_id=aid
                )
                if raw is not None:
                    ancestor = find_scrollable_ancestor(raw, max_levels=20)
                    return ancestor or raw
            except Exception:
                pass
        return self._resolve_sidebar_scroll_raw(merged)

    @staticmethod
    def _sidebar_keyboard_nudge(merged: list, direction: str, pages: float = 1.0) -> None:
        """PageDown/PageUp at sidebar list center when ScrollPattern does not realize rows."""
        import time

        if not merged:
            return
        xs: list[int] = []
        ys: list[int] = []
        for wrapper in merged:
            det = _pywinauto_to_element(wrapper)
            if not det:
                continue
            w = int(det.width or 0)
            h = int(det.height or 0)
            if w <= 0 or h <= 0:
                continue
            xs.append(int(det.x or 0) + w // 2)
            ys.append(int(det.y or 0) + h // 2)
        if not xs:
            return
        cx = int(sum(xs) / len(xs))
        cy = max(ys)
        try:
            import pyautogui

            pyautogui.moveTo(cx, cy)
            key = "pagedown" if direction == "down" else "pageup"
            presses = max(1, int(round(float(pages))))
            for _ in range(presses):
                pyautogui.press(key)
                time.sleep(0.05)
        except Exception:
            pass

    def _bottom_chat_automation_id(self, merged: list) -> str:
        chat_aids: list[tuple[int, str]] = []
        for wrapper in merged:
            det = _pywinauto_to_element(wrapper)
            if not det:
                continue
            name = (det.name or "").strip()
            aid = (getattr(det, "automation_id", "") or "").strip()
            if name.startswith("Chat ") and aid:
                chat_aids.append((int(det.y or 0), aid))
        if not chat_aids:
            return ""
        chat_aids.sort(key=lambda item: item[0])
        return chat_aids[-1][1]

    def _sidebar_scroll_via_automation_id(
        self, window, bottom_aid: str, direction: str, *, vertical_percent: float | None = None
    ) -> bool:
        """Scroll sidebar list without re-entering ui_automation (avoids list_elements recursion)."""
        if not bottom_aid:
            return False
        try:
            from detection.uia_patterns import apply_scroll_pattern, find_scrollable_ancestor

            raw = _find_raw_by_automation_id(window, bottom_aid)
            if raw is None:
                return False
            scroll_raw = find_scrollable_ancestor(raw, max_levels=20) or raw
            v_pct = vertical_percent if vertical_percent is not None else None
            result = apply_scroll_pattern(
                scroll_raw,
                direction=direction,
                amount="large",
                repeat=1,
                vertical_percent=v_pct,
            )
            return bool(result.get("success"))
        except Exception:
            return False

    def _collect_treeitem_findall(self, window, cap: int) -> list:
        """UIA FindAll(TreeItem) + sidebar scroll sweep for virtualized rows."""
        import time

        prune_left = _window_prune_left_abs(window)
        merged = self._findall_sidebar_treeitems(window, prune_left)
        if len(merged) < _SIDEBAR_TREE_MIN_ITEMS:
            return []

        if len(merged) >= _SIDEBAR_TREE_FULL_ITEMS:
            return merged

        target_more = 25
        bottom_aid = self._bottom_chat_automation_id(merged)

        if bottom_aid and len(merged) < target_more:
            self._sidebar_scroll_via_automation_id(
                window, bottom_aid, "down", vertical_percent=100.0
            )
            time.sleep(0.03)
            merged = self._merge_treeitem_wrappers(
                merged,
                self._findall_sidebar_treeitems(window, prune_left),
            )
            for _ in range(3):
                if len(merged) >= target_more:
                    break
                prev_count = len(merged)
                self._sidebar_scroll_via_automation_id(
                    window, bottom_aid, "down"
                )
                time.sleep(0.03)
                merged = self._merge_treeitem_wrappers(
                    merged,
                    self._findall_sidebar_treeitems(window, prune_left),
                )
                if len(merged) == prev_count:
                    break
            self._sidebar_scroll_via_automation_id(
                window, bottom_aid, "up", vertical_percent=0.0
            )
        else:
            scroll_raw = self._scroll_raw_for_sidebar_chat(merged)
            if scroll_raw is not None and len(merged) < target_more:
                from detection.uia_patterns import apply_scroll_pattern

                apply_scroll_pattern(
                    scroll_raw,
                    direction="down",
                    amount="large",
                    repeat=1,
                    vertical_percent=100.0,
                )
                time.sleep(0.03)
                merged = self._merge_treeitem_wrappers(
                    merged,
                    self._findall_sidebar_treeitems(window, prune_left),
                )
                apply_scroll_pattern(
                    scroll_raw,
                    direction="up",
                    amount="large",
                    repeat=1,
                    vertical_percent=0.0,
                )

        if len(merged) >= _SIDEBAR_TREE_MIN_ITEMS:
            return merged
        return []

    def _collect_treeitem_from_narrow_panes(self, window, cap: int) -> list:
        """Shallow pick left-column panes, then typed TreeItem descendants only."""
        prune_left = _window_prune_left_abs(window)
        collected: list = []
        seen: set[int] = set()
        try:
            roots = window.children()
        except Exception:
            roots = []
        for root in roots or []:
            det = _pywinauto_to_element(root)
            if not det:
                continue
            left = int(det.x or 0)
            width = int(det.width or 0)
            if left > prune_left or width > _SIDEBAR_TREE_MAX_WIDTH:
                continue
            try:
                items = root.descendants(control_type="TreeItem", depth=cap)
            except Exception:
                continue
            for item in items or []:
                key = id(getattr(item, "element_info", item))
                if key in seen:
                    continue
                seen.add(key)
                collected.append(item)
        if len(collected) >= _SIDEBAR_TREE_MIN_ITEMS:
            return collected
        return []

    def _collect_treeitem_comtypes_spatial(self, window, cap: int) -> list:
        """Fast TreeItem list: comtypes walk with left-column prune (Electron sidebars)."""
        try:
            raw = window.element_info.element
        except Exception:
            return []
        prune_left = _window_prune_left_abs(window)
        try:
            items = _walk_treeitems_spatial_pruned(
                raw, cap, prune_left_abs=prune_left
            )
        except Exception:
            return []
        if len(items) >= _SIDEBAR_TREE_MIN_ITEMS:
            return items
        return []

    def _collect_treeitem_via_sidebar_roots(
        self, window, cap: int
    ) -> list:
        """TreeItem from narrow Tree roots before full-window descendants walk."""
        collected: list = []
        seen: set[int] = set()
        try:
            tree_roots = window.descendants(control_type="Tree", depth=5)
        except Exception:
            tree_roots = []
        for root in tree_roots or []:
            det = _pywinauto_to_element(root)
            if not det:
                continue
            w = int(det.width or 0)
            if w < _SIDEBAR_TREE_MIN_WIDTH or w > _SIDEBAR_TREE_MAX_WIDTH:
                continue
            try:
                items = root.descendants(control_type="TreeItem", depth=cap)
            except Exception:
                continue
            for item in items or []:
                key = id(getattr(item, "element_info", item))
                if key in seen:
                    continue
                seen.add(key)
                collected.append(item)
        if len(collected) >= _SIDEBAR_TREE_MIN_ITEMS:
            return collected
        return []

    def _window_hwnd(self, window) -> int:
        try:
            return int(getattr(window, "handle", 0) or window.element_info.handle or 0)
        except Exception:
            return 0

    def _collect_typed_role_elements(
        self, window, max_depth: int, role_lower: str
    ) -> list:
        """UIA control_type filter — faster than full subtree walk + role filter."""
        control_type = _TYPED_ROLE_CONTROL.get(role_lower)
        if not control_type:
            return []
        requested = max(4, min(int(max_depth or 6), 10))
        cap = requested
        if role_lower == "treeitem":
            hwnd = self._window_hwnd(window)

            def _fetch_treeitems() -> list:
                for collector in (
                    self._collect_treeitem_findall,
                    self._collect_treeitem_from_narrow_panes,
                    self._collect_treeitem_comtypes_spatial,
                    self._collect_treeitem_via_sidebar_roots,
                ):
                    items = collector(window, cap)
                    if items:
                        return items
                return []

            if hwnd:
                from detection.uia_tree_cache import get_descendants

                cached = get_descendants(
                    hwnd,
                    _fetch_treeitems,
                    scope=f"treeitem:{cap}",
                    ttl_s=60.0,
                )
                if cached:
                    return cached
            direct = _fetch_treeitems()
            if direct:
                return direct

        def _fetch_full_window() -> list:
            try:
                elems = window.descendants(control_type=control_type, depth=cap)
                if elems:
                    return elems
            except Exception:
                pass
            try:
                return window.descendants(depth=cap)
            except Exception:
                return []

        hwnd = self._window_hwnd(window)
        if hwnd:
            from detection.uia_tree_cache import get_descendants

            return get_descendants(
                hwnd,
                _fetch_full_window,
                scope=f"typed:{role_lower}:{cap}",
                ttl_s=30.0,
            )
        return _fetch_full_window()

    def _legacy_dict_to_detected(self, d: dict) -> DetectedElement:
        return DetectedElement(
            name=d.get("name", ""),
            role=d.get("role", ""),
            x=d.get("x", 0),
            y=d.get("y", 0),
            width=d.get("width", 0),
            height=d.get("height", 0),
            value=d.get("value", ""),
            backend=d.get("backend", "spy"),
            automation_id=d.get("automation_id", ""),
            class_name=d.get("class_name", ""),
            framework_id=d.get("framework_id", ""),
            process_id=int(d.get("process_id", 0) or 0),
            visible=d.get("visible", True),
            enabled=d.get("enabled", True),
            clickable_x=d.get("clickable_x"),
            clickable_y=d.get("clickable_y"),
            patterns=d.get("patterns", []),
        )

    def _try_spy_find(
        self,
        name: Optional[str],
        automation_id: Optional[str],
        window_title: Optional[str],
        role: Optional[str],
    ) -> list[DetectedElement]:
        if not (name or automation_id):
            return []
        try:
            from tools.spy_bridge import spy_available, spy_find_element
            if not spy_available():
                return []
            elem = spy_find_element(
                name=name,
                automation_id=automation_id,
                window_title=window_title,
                role=role,
            )
            if elem:
                return [self._legacy_dict_to_detected(elem)]
        except Exception:
            pass
        return []

    def list_elements(
        self,
        window_title: Optional[str] = None,
        max_depth: int = 12,
        role: Optional[str] = None,
        tree_mode: str = "control",
        include_offscreen: bool = False,
        window_handle: Optional[int] = None,
        view_scope: bool = False,
    ) -> list[DetectedElement]:
        if not self.is_available():
            return []
        desktop = _get_desktop()
        window = _resolve_window(desktop, window_title, window_handle=window_handle)
        if not window:
            return []
        walk_root = window
        role_lower_scope = (role or "").strip().lower()
        if view_scope and role_lower_scope not in _TYPED_ROLE_CONTROL:
            try:
                from detection.spatial_cluster import resolve_content_walk_root

                scoped = resolve_content_walk_root(window)
                if scoped is not None:
                    walk_root = scoped
            except Exception:
                pass
        try:
            descendants = self._collect_descendants(walk_root, tree_mode, max_depth, role)
        except Exception:
            return []

        role_lower = role.lower() if role else None
        elements = []
        for elem in descendants:
            d = _pywinauto_to_element(elem)
            if not d:
                continue
            if role_lower and (d.role or "").lower() != role_lower:
                continue
            if not _element_useful(d, include_offscreen):
                continue
            elements.append(d)

        try:
            from tools.spy_bridge import spy_available, spy_list_elements
            role_lower = role.lower() if role else None
            skip_spy = _should_skip_spy_list(
                window_title, role_lower, bool(elements)
            )
            if spy_available() and not skip_spy:
                spy_elems = spy_list_elements(
                    window_title=window_title or "",
                    max_depth=max_depth,
                    role_filter=role or "",
                    visible_only=not include_offscreen,
                )
                seen = {(d.automation_id, d.x, d.y) for d in elements}
                for raw in spy_elems:
                    d = self._legacy_dict_to_detected(raw)
                    if role_lower and (d.role or "").lower() != role_lower:
                        continue
                    if not _element_useful(d, include_offscreen):
                        continue
                    key = (d.automation_id, d.x, d.y)
                    if key in seen:
                        continue
                    elements.append(d)
                    seen.add(key)
        except Exception:
            pass

        try:
            from tools.framework_detect import do_detect_framework
            if do_detect_framework(window_title).get("framework") in ("uwp", "winui"):
                xaml_only = [
                    d for d in elements
                    if (d.framework_id or "").upper() == "XAML"
                ]
                if len(xaml_only) >= 10:
                    elements = xaml_only
        except Exception:
            pass

        from detection.element_dedupe import dedupe_detected_elements
        elements = dedupe_detected_elements(elements)
        return elements

    def find_elements(
        self,
        name: Optional[str] = None,
        role: Optional[str] = None,
        automation_id: Optional[str] = None,
        class_name: Optional[str] = None,
        window_title: Optional[str] = None,
        tree_mode: str = "control",
        include_offscreen: bool = False,
        index: int = 0,
        window_handle: Optional[int] = None,
    ) -> list[DetectedElement]:
        desktop = _get_desktop()
        window = _resolve_window(desktop, window_title, window_handle=window_handle)
        uia_first = _prefer_uia_find_before_spy(window_title)

        if window and automation_id:
            from detection.automation_id_aliases import alias_candidates

            for aid_try in alias_candidates(automation_id):
                raw = _find_raw_by_automation_id(window, aid_try)
                if raw:
                    d = _pywinauto_to_element(raw)
                    if d and _matches(d, name, role, automation_id, class_name):
                        return [d]
                    if d and _matches(d, name, role, aid_try, class_name):
                        return [d]
            try:
                from detection.element_model import DetectedElement
                from tools.spy_bridge import (
                    spy_available,
                    spy_inspect_element,
                    spy_props_to_element,
                )

                def _spy_to_detected(props: dict, aid: str) -> Optional[DetectedElement]:
                    elem = spy_props_to_element(
                        props.get("properties") or props,
                        window_title=window_title,
                    )
                    if not elem:
                        return None
                    return DetectedElement(
                        name=elem.get("name", ""),
                        role=elem.get("role", ""),
                        automation_id=elem.get("automation_id", aid),
                        x=int(elem.get("x", 0) or 0),
                        y=int(elem.get("y", 0) or 0),
                        width=int(elem.get("width", 0) or 0),
                        height=int(elem.get("height", 0) or 0),
                    )

                if spy_available():
                    hit = spy_inspect_element(
                        automation_id=automation_id,
                        window_title=window_title,
                    )
                    if hit.get("found"):
                        d = _spy_to_detected(hit, automation_id)
                        if d and _matches(d, name, role, automation_id, class_name):
                            return [d]
                    else:
                        for alt in alias_candidates(automation_id)[1:]:
                            alt_hit = spy_inspect_element(
                                automation_id=alt,
                                window_title=window_title,
                            )
                            if not alt_hit.get("found"):
                                continue
                            d = _spy_to_detected(alt_hit, alt)
                            if d and _matches(d, name, role, alt, class_name):
                                return [d]
                            raw = _find_raw_by_automation_id(window, alt)
                            if raw:
                                d = _pywinauto_to_element(raw)
                                if d and _matches(d, name, role, alt, class_name):
                                    return [d]
                        return []
            except Exception:
                pass
            return []

        if window and (name or automation_id) and uia_first:
            raw = _find_raw_direct(window, name=name, role=role, automation_id=automation_id)
            if raw:
                d = _pywinauto_to_element(raw)
                if d and _matches(d, name, role, automation_id, class_name):
                    return [d]

        spy_hits: list[DetectedElement] = []
        if not uia_first and not automation_id:
            spy_hits = self._try_spy_find(name, automation_id, window_title, role)
            if spy_hits:
                matches = [d for d in spy_hits if _matches(d, name, role, automation_id, class_name)]
                if matches:
                    if index > 0:
                        idx = min(index, len(matches) - 1)
                        return [matches[idx]]
                    return matches

        if window and (name or automation_id) and not uia_first and not automation_id:
            raw = _find_raw_direct(window, name=name, role=role, automation_id=automation_id)
            if raw:
                d = _pywinauto_to_element(raw)
                if d and _matches(d, name, role, automation_id, class_name):
                    return [d]

        depth_ladder = _FIND_DEPTH_LADDER_AUTOMATION_ID if automation_id else _FIND_DEPTH_LADDER
        for depth in depth_ladder:
            all_elems = self.list_elements(
                window_title=window_title,
                max_depth=depth,
                role=role,
                tree_mode=tree_mode,
                include_offscreen=include_offscreen,
                window_handle=window_handle,
            )
            matches = [
                d for d in all_elems
                if _matches(d, name, role, automation_id, class_name)
            ]
            if matches:
                if index > 0:
                    idx = min(index, len(matches) - 1)
                    return [matches[idx]]
                return matches
        return []

    def element_at_point(self, x: int, y: int) -> Optional[DetectedElement]:
        if not self.is_available():
            return None
        try:
            from pywinauto.uia_element_info import UIAElementInfo
            from pywinauto.controls.uiawrapper import UIAWrapper
            info = UIAElementInfo.from_point(x, y)
            wrapper = UIAWrapper(info)
            return _pywinauto_to_element(wrapper)
        except Exception:
            return None

    def get_properties(self, element: DetectedElement) -> dict:
        d = element.to_dict()
        d["raw_properties"] = element.raw_properties or {}
        return d

    def _find_raw_element(self, name: str = "", role: str = "", window_title: Optional[str] = None):
        desktop = _get_desktop()
        window = _resolve_window(desktop, window_title)
        if not window:
            return None, None
        for elem in window.descendants():
            d = _pywinauto_to_element(elem)
            if not d:
                continue
            if name and name.lower() not in (d.name or "").lower():
                continue
            if role and role.lower() not in (d.role or "").lower():
                continue
            return elem, d
        return None, None

    def invoke_element_by_name(
        self,
        name: str,
        role: str = "",
        window_title: Optional[str] = None,
    ) -> dict:
        try:
            from pywinauto.uia_defines import get_elem_interface
            elem, _ = self._find_raw_element(name=name, role=role, window_title=window_title)
            if not elem:
                return {"success": False, "error": "element not found"}
            pattern = get_elem_interface(elem.element_info.element, "Invoke")
            pattern.Invoke()
            return {"success": True, "method": "InvokePattern"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def expand_element(
        self,
        name: str = "",
        role: str = "MenuItem",
        window_title: Optional[str] = None,
    ) -> dict:
        try:
            from pywinauto.uia_defines import get_elem_interface
            elem, _ = self._find_raw_element(name=name, role=role, window_title=window_title)
            if not elem:
                return {"success": False, "error": "element not found"}
            pattern = get_elem_interface(elem.element_info.element, "ExpandCollapse")
            pattern.Expand()
            return {"success": True, "method": "ExpandCollapse.Expand"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def collapse_element(
        self,
        name: str = "",
        role: str = "",
        window_title: Optional[str] = None,
    ) -> dict:
        try:
            from pywinauto.uia_defines import get_elem_interface
            elem, _ = self._find_raw_element(name=name, role=role, window_title=window_title)
            if not elem:
                return {"success": False, "error": "element not found"}
            pattern = get_elem_interface(elem.element_info.element, "ExpandCollapse")
            pattern.Collapse()
            return {"success": True, "method": "ExpandCollapse.Collapse"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _resolve_raw_element(
        self,
        element: DetectedElement,
        window_title: Optional[str] = None,
    ):
        desktop = _get_desktop()
        window = _resolve_window(desktop, window_title)
        if not window:
            return None, "Window not found"
        raw = None
        if element.automation_id:
            raw = _find_raw_by_automation_id(window, element.automation_id)
        if raw is None:
            raw, _ = self._find_raw_element(
                name=element.name,
                role=element.role,
                window_title=window_title,
            )
        if not raw:
            return None, "Element not found"
        return raw, None

    def expand_collapse_element(
        self,
        element: DetectedElement,
        action: str = "expand",
        window_title: Optional[str] = None,
    ) -> dict:
        """Expand or collapse via UIA ExpandCollapsePattern."""
        try:
            from pywinauto.uia_defines import get_elem_interface
            raw, err = self._resolve_raw_element(element, window_title)
            if not raw:
                return {"success": False, "error": err or "Element not found"}
            pattern = get_elem_interface(raw.element_info.element, "ExpandCollapse")
            collapse = (action or "expand").lower() == "collapse"
            if collapse:
                pattern.Collapse()
                return {"success": True, "method": "ExpandCollapse.Collapse"}
            pattern.Expand()
            return {"success": True, "method": "ExpandCollapse.Expand"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def invoke_element(self, element: DetectedElement, window_title: Optional[str] = None) -> dict:
        try:
            from pywinauto.uia_defines import get_elem_interface
            raw, err = self._resolve_raw_element(element, window_title)
            if not raw:
                return {"success": False, "error": err or "Element not found for invoke"}
            element_iface = raw.element_info.element
            for pattern_name, invoke_fn in (
                ("Invoke", lambda p: p.Invoke()),
                ("Toggle", lambda p: p.Toggle()),
                ("SelectionItem", lambda p: p.Select()),
                ("ExpandCollapse", lambda p: p.Expand()),
            ):
                try:
                    pattern = get_elem_interface(element_iface, pattern_name)
                    invoke_fn(pattern)
                    method = f"{pattern_name}Pattern"
                    if pattern_name == "ExpandCollapse":
                        method = "ExpandCollapse.Expand"
                    return {"success": True, "method": method}
                except Exception:
                    continue
            return {
                "success": False,
                "error": "No Invoke/Toggle/SelectionItem/ExpandCollapse pattern available",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def focus_element(
        self,
        element: DetectedElement,
        window_title: Optional[str] = None,
    ) -> dict:
        """Move keyboard focus to an element via UIA SetFocus."""
        try:
            raw, err = self._resolve_raw_element(element, window_title)
            if not raw:
                return {"success": False, "error": err or "Element not found for focus"}
            raw.set_focus()
            return {"success": True, "method": "SetFocus"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_element_value(
        self, element: DetectedElement, value: str, window_title: Optional[str] = None,
    ) -> dict:
        try:
            from pywinauto.uia_defines import get_elem_interface
            desktop = _get_desktop()
            window = _resolve_window(desktop, window_title)
            if not window:
                return {"success": False, "error": "Window not found"}
            raw = None
            if element.automation_id:
                raw = _find_raw_by_automation_id(window, element.automation_id)
            if raw is None:
                raw, _ = self._find_raw_element(
                    name=element.name,
                    role=element.role,
                    window_title=window_title,
                )
            if not raw:
                return {"success": False, "error": "ValuePattern not available"}
            pattern = get_elem_interface(raw.element_info.element, "Value")
            pattern.SetValue(value)
            return {"success": True, "method": "ValuePattern"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def ensure_chromium_accessibility(self, window_title: Optional[str] = None) -> dict:
        """Subscribe to UIA events to encourage Chromium to expose its tree."""
        try:
            from tools.framework_detect import do_detect_framework
            fw = do_detect_framework(window_title)
            if fw.get("framework") not in ("electron", "chromium_browser"):
                return {"triggered": False, "reason": "not chromium"}
            elements = self.list_elements(window_title=window_title, max_depth=3)
            named = [e for e in elements if e.name.strip()]
            if len(named) >= 5:
                return {"triggered": False, "reason": "tree already populated"}
            iuia = _get_iuia().iuia
            desktop = _get_desktop()
            window = _resolve_window(desktop, window_title)
            if not window:
                return {"triggered": False, "error": "window not found"}
            # Register brief structure-changed handler to wake renderer bridge
            try:
                handler = iuia.CreateEventHandler()
                iuia.iuia.AddStructureChangedEventHandler(
                    window.element_info.element,
                    1,  # TreeScope_Subtree
                    None,
                    handler,
                )
            except Exception:
                pass
            return {
                "triggered": True,
                "hint": "Relaunch with --force-renderer-accessibility if tree stays empty",
                "named_elements": len(named),
            }
        except Exception as e:
            return {"triggered": False, "error": str(e)}


def get_uia_backend() -> UIABackend:
    return UIABackend()

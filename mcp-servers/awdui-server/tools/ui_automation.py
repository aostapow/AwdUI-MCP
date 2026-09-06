"""UI Automation tools -- find and click elements by name/role.

Uses multi-backend detection (UIA, MSAA, Win32, JAB, FlaUI) via detection.orchestrator.
Falls back to OCR and visual detection through smart_find.
"""
from __future__ import annotations

import hashlib
import sys
from difflib import SequenceMatcher
from typing import Optional

from tools.input_tools import do_click


def _orch():
    from detection.orchestrator import get_orchestrator
    return get_orchestrator()


def _legacy_element(elem: dict) -> dict:
    """Ensure legacy keys exist for callers expecting old format."""
    out = {
        "name": elem.get("name", ""),
        "role": elem.get("role", ""),
        "x": elem.get("x", 0),
        "y": elem.get("y", 0),
        "width": elem.get("width", 0),
        "height": elem.get("height", 0),
        "value": elem.get("value", ""),
        "automation_id": elem.get("automation_id", ""),
        "class_name": elem.get("class_name", ""),
        "framework_id": elem.get("framework_id", ""),
        "visible": elem.get("visible", True),
        "enabled": elem.get("enabled", True),
        "backend": elem.get("backend", "uia"),
        "patterns": elem.get("patterns", []),
    }
    for key in ("clickable_x", "clickable_y", "center_x", "center_y"):
        if elem.get(key) is not None:
            out[key] = elem[key]
    return out


def _do_find_element_darwin(
    name: Optional[str] = None,
    role: Optional[str] = None,
    window_title: Optional[str] = None,
    automation_id: Optional[str] = None,
    class_name: Optional[str] = None,
    tree_mode: str = "control",
    include_offscreen: bool = False,
    index: int = 0,
) -> dict:
    from awdui_platform.darwin_backend import (
        ax_get_frontmost_app,
        ax_get_app_for_title,
        ax_find_elements,
    )

    if window_title:
        root = ax_get_app_for_title(window_title)
        if root is None:
            return {"found": False, "elements": [], "error": f"Window '{window_title}' not found"}
    else:
        root = ax_get_frontmost_app()
        if root is None:
            return {"found": False, "elements": [], "error": "No frontmost application found"}

    matches = ax_find_elements(root, name=name, role=role)
    if not matches:
        return {"found": False, "elements": []}
    if index > 0:
        idx = min(index, len(matches) - 1)
        return {"found": True, "elements": [matches[idx]]}
    return {"found": True, "elements": matches}


def _do_list_elements_darwin(
    window_title: Optional[str] = None,
    max_depth: int = 5,
    role: Optional[str] = None,
) -> dict:
    from awdui_platform.darwin_backend import (
        ax_get_frontmost_app,
        ax_get_app_for_title,
        ax_find_elements,
    )

    if window_title:
        root = ax_get_app_for_title(window_title)
        if root is None:
            return {"elements": [], "error": f"Window '{window_title}' not found"}
    else:
        root = ax_get_frontmost_app()
        if root is None:
            return {"elements": [], "error": "No frontmost application found"}

    depth = 100 if role else max_depth
    all_elements = ax_find_elements(root, role=role, max_depth=depth)
    return {"elements": all_elements, "count": len(all_elements)}


def do_find_element(
    name: Optional[str] = None,
    role: Optional[str] = None,
    window_title: Optional[str] = None,
    index: int = 0,
    automation_id: Optional[str] = None,
    class_name: Optional[str] = None,
    tree_mode: str = "control",
    include_offscreen: bool = False,
    remember: bool = True,
    window_handle: Optional[int] = None,
) -> dict:
    import time
    from tools.action_timing import attach_simple_elapsed
    from tools.app_session import normalize_index

    index = normalize_index(index)

    t0 = time.perf_counter()
    if sys.platform == "darwin":
        out = _do_find_element_darwin(
            name, role, window_title, automation_id, class_name, tree_mode, include_offscreen, index,
        )
        return attach_simple_elapsed(out, t0)

    repo_result = None
    try:
        from detection.repo_lookup import resolve_via_repository
        repo_result = resolve_via_repository(
            _orch(),
            name=name,
            role=role,
            automation_id=automation_id,
            window_title=window_title,
            index=index,
        )
    except Exception:
        pass
    if repo_result and repo_result.get("found"):
        if remember and repo_result.get("elements"):
            try:
                from detection.auto_repo import maybe_remember_element
                path = maybe_remember_element(
                    repo_result["elements"][min(index, len(repo_result["elements"]) - 1)],
                    window_title=window_title,
                    repo_path=repo_result.get("repo_path"),
                    backend=repo_result.get("backend_used", "repository"),
                    remember=remember,
                )
                if path:
                    repo_result["repo_path"] = path
            except Exception:
                pass
        return attach_simple_elapsed(repo_result, t0)

    result = _orch().find_elements(
        name=name,
        role=role,
        automation_id=automation_id,
        class_name=class_name,
        window_title=window_title,
        tree_mode=tree_mode,
        include_offscreen=include_offscreen,
        index=index,
        window_handle=window_handle,
    )
    if not result.get("found"):
        return attach_simple_elapsed(
            {"found": False, "elements": [], "error": result.get("error", "")},
            t0,
        )
    from detection.element_coords import to_screen_coords

    elements = [to_screen_coords(_legacy_element(e), window_title) for e in result["elements"]]
    backend = result.get("backend_used", "uia")
    if remember and elements:
        try:
            from detection.auto_repo import maybe_remember_element
            path = maybe_remember_element(
                elements[min(index, len(elements) - 1)] if index else elements[0],
                window_title=window_title,
                backend=backend,
                remember=remember,
            )
            if path:
                result["repo_path"] = path
        except Exception:
            pass
    return attach_simple_elapsed(
        {
            "found": True,
            "elements": elements,
            "backend_used": backend,
            **({"repo_path": result["repo_path"]} if result.get("repo_path") else {}),
        },
        t0,
    )


def do_list_elements(
    window_title: Optional[str] = None,
    max_depth: Optional[int] = None,
    role: Optional[str] = None,
    tree_mode: str = "control",
    include_offscreen: bool = False,
    window_handle: Optional[int] = None,
    adaptive_cluster: bool = True,
) -> dict:
    import time
    from detection.tree_depth import resolve_list_depth
    from tools.action_timing import attach_simple_elapsed

    requested, effective, fw = resolve_list_depth(
        max_depth, role=role, window_title=window_title,
    )
    t0 = time.perf_counter()
    if sys.platform == "darwin":
        out = _do_list_elements_darwin(window_title, effective, role)
        out["max_depth_requested"] = requested
        out["max_depth_effective"] = effective
        if fw:
            out["framework_depth"] = fw
        return attach_simple_elapsed(out, t0)

    out = _orch().list_elements(
        window_title=window_title,
        max_depth=effective,
        role=role,
        tree_mode=tree_mode,
        include_offscreen=include_offscreen,
        window_handle=window_handle,
        adaptive_cluster=adaptive_cluster,
    )
    out["max_depth_requested"] = requested
    out["max_depth_effective"] = effective
    if fw:
        out["framework_depth"] = fw
    return attach_simple_elapsed(out, t0)


def do_element_at_point(x: int, y: int) -> dict:
    if sys.platform == "darwin":
        return {"found": False, "error": "element_at_point not implemented on macOS yet"}
    return _orch().element_at_point(x, y)


def do_get_element_properties(
    name: Optional[str] = None,
    automation_id: Optional[str] = None,
    x: Optional[int] = None,
    y: Optional[int] = None,
    window_title: Optional[str] = None,
    window_handle: Optional[int] = None,
) -> dict:
    if sys.platform == "darwin":
        return {"found": False, "error": "get_element_properties not implemented on macOS yet"}
    return _orch().get_element_properties(
        name=name,
        automation_id=automation_id,
        x=x,
        y=y,
        window_title=window_title,
        window_handle=window_handle,
    )


def _elements_inside_parent(parent: dict, candidates: list[dict], limit: int = 12) -> list[dict]:
    px = int(parent.get("x", 0) or 0)
    py = int(parent.get("y", 0) or 0)
    pw = int(parent.get("width", 0) or 0)
    ph = int(parent.get("height", 0) or 0)
    if pw <= 0 or ph <= 0:
        return []
    parent_aid = (parent.get("automation_id") or "").strip()
    out: list[dict] = []
    for elem in candidates:
        aid = (elem.get("automation_id") or "").strip()
        if aid and aid == parent_aid:
            continue
        cx = int(elem.get("x", 0) or 0) + int(elem.get("width", 0) or 0) // 2
        cy = int(elem.get("y", 0) or 0) + int(elem.get("height", 0) or 0) // 2
        if px <= cx <= px + pw and py <= cy <= py + ph:
            out.append(elem)
            if len(out) >= limit:
                break
    return out


def do_discover_control_interaction(
    name: Optional[str] = None,
    automation_id: Optional[str] = None,
    window_title: Optional[str] = None,
    x: Optional[int] = None,
    y: Optional[int] = None,
    include_children: bool = True,
) -> dict:
    """Inspect control and return generic interaction strategies (no app-specific rules)."""
    from detection.control_interaction import discover_from_element, format_discovery_report

    if sys.platform != "win32":
        return {
            "success": False,
            "error": "discover_control_interaction is Windows-only",
        }

    element: Optional[dict] = None
    props: dict = {}

    if x is not None and y is not None and x >= 0 and y >= 0:
        hit = do_element_at_point(x, y)
        if hit.get("found"):
            element = hit.get("element") or {}
    else:
        from tools.spy_bridge import spy_available, spy_inspect_element, spy_props_to_element

        if spy_available() and (automation_id or name):
            spy = spy_inspect_element(
                name=name,
                automation_id=automation_id,
                window_title=window_title,
            )
            if spy.get("found"):
                props = spy.get("properties") or {}
                element = spy_props_to_element(props, window_title=window_title)
        if not element:
            found = do_find_element(
                name=name,
                automation_id=automation_id,
                window_title=window_title,
                include_offscreen=True,
            )
            if found.get("found") and found.get("elements"):
                element = found["elements"][0]

    if not element:
        return {
            "success": False,
            "error": "Element not found",
            "report_text": "Element not found for discover_control_interaction.",
        }

    children: list[dict] = []
    if include_children and (element.get("role") or "") in {
        "Pane",
        "Group",
        "Custom",
        "Window",
        "Document",
        "Tab",
    }:
        listing = do_list_elements(window_title=window_title, max_depth=5)
        children = _elements_inside_parent(element, listing.get("elements") or [])

    repo_hints = ""
    aid = (element.get("automation_id") or "").strip()
    if aid:
        try:
            from detection.repo_store import get_hints_by_automation_id

            repo_hints = get_hints_by_automation_id(aid)
        except Exception:
            repo_hints = ""

    pattern_states: dict = {}
    if props:
        raw_patterns = props.get("patterns") or {}
        if isinstance(raw_patterns, dict) and "Value" in raw_patterns:
            pattern_states["Value"] = raw_patterns.get("Value") or {}

    report = discover_from_element(
        element,
        children=children or None,
        pattern_states=pattern_states or None,
        repo_hints=repo_hints,
    )
    return {
        "success": True,
        "report": report,
        "report_text": format_discovery_report(report),
    }


def _resolve_verify_target(
    acted_aid: Optional[str],
    verify_automation_id: Optional[str],
    verify_name_contains: Optional[str],
    window_title: Optional[str],
) -> Optional[str]:
    """Pick UIA node for post-act verify — explicit param, then repo agent_hints."""
    explicit = (verify_automation_id or "").strip()
    if explicit:
        return explicit
    needle = (verify_name_contains or "").strip()
    aid = (acted_aid or "").strip()
    if not needle or not aid:
        return aid or None
    try:
        from detection.agent_hints import hint_verify_automation_id
        from detection.repo_store import get_hints_by_automation_id

        repo_target = hint_verify_automation_id(get_hints_by_automation_id(aid))
        if repo_target:
            from tools.spy_bridge import spy_available, spy_verify_live

            if spy_available():
                live = spy_verify_live(
                    automation_id=repo_target,
                    window_title=window_title,
                    require_enabled=False,
                )
                if live.get("live"):
                    return repo_target
    except Exception:
        pass
    return aid


def _finish_action_with_verify(
    timer,
    result: dict,
    *,
    window_title: Optional[str],
    verify_automation_id: Optional[str],
    verify_name_contains: Optional[str],
    acted_automation_id: Optional[str] = None,
    verify_timeout_ms: int = 5000,
    verify_poll_ms: int = 100,
) -> dict:
    from tools.action_timing import run_post_act_verify

    needle = (verify_name_contains or "").strip()
    acted = (
        (acted_automation_id or "").strip()
        or str((result.get("element") or {}).get("automation_id") or "").strip()
    )
    verify_target = _resolve_verify_target(
        acted,
        verify_automation_id,
        verify_name_contains,
        window_title,
    )
    if verify_target or needle:
        v = run_post_act_verify(
            window_title=window_title,
            verify_automation_id=verify_target,
            verify_name_contains=needle or None,
            timeout_ms=verify_timeout_ms,
            poll_ms=verify_poll_ms,
        )
        timer.mark("verify_ms", v.get("verify_ms", 0))
        result["verified"] = v.get("verified")
        if v.get("verify_error"):
            result["verify_error"] = v["verify_error"]
        if v.get("actual_name"):
            result["verify_detail"] = v["actual_name"]
        if v.get("verify_name"):
            result["verify_name"] = v["verify_name"]
        if v.get("verified") is False:
            result["verify_target_used"] = verify_target
            if verify_target == acted and acted and needle:
                result.setdefault(
                    "hint",
                    "set verify_automation_id on the acted control via repo agent_hints "
                    "(repo_capture / repo_hints) or pass verify_automation_id explicitly",
                )
    return timer.attach(result)


def do_invoke_element(
    name: Optional[str] = None,
    automation_id: Optional[str] = None,
    window_title: Optional[str] = None,
    element: Optional[dict] = None,
    verify_automation_id: Optional[str] = None,
    verify_name_contains: Optional[str] = None,
    verify_timeout_ms: int = 5000,
    verify_poll_ms: int = 100,
) -> dict:
    from tools.action_timing import ActionTimer

    timer = ActionTimer()
    if sys.platform != "win32":
        return {"success": False, "error": "invoke_element is Windows-only", "elapsed_ms": 0}

    verify_kwargs = {
        "verify_timeout_ms": verify_timeout_ms,
        "verify_poll_ms": verify_poll_ms,
    }

    if element:
        timer.start("act")
        result = do_invoke_on_element(element, window_title=window_title)
        timer.end()
        return _finish_action_with_verify(
            timer,
            result,
            window_title=window_title,
            verify_automation_id=verify_automation_id,
            verify_name_contains=verify_name_contains,
            acted_automation_id=(element or {}).get("automation_id") or automation_id,
            **verify_kwargs,
        )
    stale = _stale_instance_probe(automation_id, window_title)
    timer.end()
    if stale:
        return timer.attach(stale)

    try:
        from tools.framework_detect import do_detect_framework
        fw = do_detect_framework(window_title).get("framework", "")
        if fw in ("uwp", "winui"):
            from tools.spy_bridge import spy_invoke_element, spy_available
            if spy_available():
                timer.start("act")
                spy = spy_invoke_element(
                    name=name, automation_id=automation_id, window_title=window_title,
                )
                timer.end()
                if spy.get("success"):
                    return _finish_action_with_verify(
                        timer,
                        spy,
                        window_title=window_title,
                        verify_automation_id=verify_automation_id,
                        verify_name_contains=verify_name_contains,
                        acted_automation_id=automation_id,
                        **verify_kwargs,
                    )
    except Exception:
        pass

    timer.start("find")
    matches = do_find_element(
        name=name,
        automation_id=automation_id,
        window_title=window_title,
        include_offscreen=True,
        remember=False,
    )
    timer.end()
    if not matches.get("found"):
        from tools.spy_bridge import spy_invoke_element
        timer.start("act")
        spy = spy_invoke_element(
            name=name, automation_id=automation_id, window_title=window_title,
        )
        timer.end()
        if spy.get("success"):
            return _finish_action_with_verify(
                timer,
                spy,
                window_title=window_title,
                verify_automation_id=verify_automation_id,
                verify_name_contains=verify_name_contains,
                acted_automation_id=automation_id,
                **verify_kwargs,
            )
        out = {
            "success": False,
            "error": spy.get("error", "Element not found"),
        }
        return timer.attach(out)

    timer.start("act")
    result = do_invoke_on_element(matches["elements"][0], window_title=window_title)
    timer.end()
    if result.get("success"):
        return _finish_action_with_verify(
            timer,
            result,
            window_title=window_title,
            verify_automation_id=verify_automation_id,
            verify_name_contains=verify_name_contains,
            acted_automation_id=automation_id,
            **verify_kwargs,
        )

    from tools.spy_bridge import spy_invoke_element
    timer.start("act")
    spy = spy_invoke_element(
        name=name or matches["elements"][0].get("name"),
        automation_id=automation_id or matches["elements"][0].get("automation_id"),
        window_title=window_title,
    )
    timer.end()
    if spy.get("success"):
        return _finish_action_with_verify(
            timer,
            spy,
            window_title=window_title,
            verify_automation_id=verify_automation_id,
            verify_name_contains=verify_name_contains,
            acted_automation_id=automation_id,
            **verify_kwargs,
        )
    return timer.attach(result)


def _stale_instance_probe(
    automation_id: Optional[str],
    window_title: Optional[str],
) -> Optional[dict]:
    """Return error dict if spy sees disabled/missing element (orphan Calculator instance)."""
    if not automation_id:
        return None
    try:
        from tools.spy_bridge import spy_available, spy_verify_live
        from detection.orchestrator import invalidate_tree_cache
        if not spy_available():
            return None
        live = spy_verify_live(automation_id=automation_id, window_title=window_title)
        if live.get("live"):
            return None
        invalidate_tree_cache(window_title)
        return {
            "success": False,
            "error": f"Stale UIA instance ({live.get('reason')})",
            "code": live.get("code", "stale_instance"),
            "hint": "launch_app(path='calc.exe', replace=true) + set_target_window; retry invoke_element",
            "probe": automation_id,
        }
    except Exception:
        return None


def _quick_resolve_element(
    name: Optional[str] = None,
    automation_id: Optional[str] = None,
    window_title: Optional[str] = None,
) -> Optional[dict]:
    """Lightweight element lookup for fallback_click — no ExpandCollapse attempts."""
    if not (automation_id or name):
        return None
    try:
        from tools.spy_bridge import spy_available, spy_inspect_element, spy_props_to_element

        if spy_available():
            props = spy_inspect_element(
                name=name, automation_id=automation_id, window_title=window_title,
            )
            if props.get("found"):
                return spy_props_to_element(
                    props.get("properties") or props, window_title=window_title,
                )
    except Exception:
        pass
    matches = do_find_element(
        name=name,
        automation_id=automation_id,
        window_title=window_title,
        include_offscreen=True,
    )
    if matches.get("found"):
        return matches["elements"][0]
    return None


def _looks_like_uwp_expander(elem: dict) -> bool:
    aid = (elem.get("automation_id") or "").lower()
    role = (elem.get("role") or "").lower()
    class_name = (elem.get("class_name") or "").lower()
    if aid.endswith("expander"):
        return True
    if "expander" in role or "settingsexpander" in class_name:
        return True
    return role == "group" and "expander" in aid


def _expand_element_fallback_header_click(
    elem: dict, window_title: Optional[str] = None
) -> dict:
    from detection.element_coords import expander_header_click_coords
    from tools.target_window import ensure_focus_for_input

    ensure_focus_for_input()
    w = int(elem.get("width") or elem.get("w") or 0)
    h = int(elem.get("height") or elem.get("h") or 0)
    if w > 0 and h > 0:
        cx, cy = expander_header_click_coords(elem, window_title)
    else:
        from tools.highlight import element_screen_bbox

        bbox = element_screen_bbox(elem, window_title=window_title)
        if bbox:
            x, y, bw, bh = bbox
            cx = x + bw // 2
            cy = y + max(1, bh // 6)
        else:
            cx, cy = expander_header_click_coords(elem, window_title)
    click_result = do_click(cx, cy)
    out = {
        "success": True,
        "method": "HeaderClick",
        "used_fallback_click": True,
        "clicked_at": {"x": cx, "y": cy},
        "element": elem,
    }
    if "navigation_warning" in click_result:
        out["navigation_warning"] = click_result["navigation_warning"]
    return out


def do_expand_element(
    name: Optional[str] = None,
    automation_id: Optional[str] = None,
    window_title: Optional[str] = None,
    action: str = "expand",
    element: Optional[dict] = None,
    fallback_click: bool = False,
) -> dict:
    import time
    t0 = time.perf_counter()
    if sys.platform != "win32":
        return {"success": False, "error": "expand_element is Windows-only", "elapsed_ms": 0}

    from detection.backends.uia_backend import get_uia_backend
    from detection.element_model import DetectedElement

    def _finish(result: dict) -> dict:
        result["elapsed_ms"] = int((time.perf_counter() - t0) * 1000)
        return result

    if fallback_click and (automation_id or name):
        quick = _quick_resolve_element(
            name=name, automation_id=automation_id, window_title=window_title,
        )
        if quick and _looks_like_uwp_expander(quick):
            out = _expand_element_fallback_header_click(quick, window_title)
            out["fast_path"] = True
            return _finish(out)

    if element:
        detected = DetectedElement(
            name=element.get("name") or "",
            role=element.get("role") or "",
            automation_id=element.get("automation_id") or "",
        )
        return _finish(
            get_uia_backend().expand_collapse_element(
                detected, action=action, window_title=window_title,
            )
        )

    try:
        from tools.framework_detect import do_detect_framework
        fw = do_detect_framework(window_title).get("framework", "")
        if fw in ("uwp", "winui"):
            from tools.spy_bridge import spy_available, spy_expand_collapse_element
            if spy_available():
                spy = spy_expand_collapse_element(
                    name=name,
                    automation_id=automation_id,
                    window_title=window_title,
                    action=action,
                )
                if spy.get("success"):
                    return _finish(spy)
    except Exception:
        pass

    matches = do_find_element(
        name=name,
        automation_id=automation_id,
        window_title=window_title,
        include_offscreen=True,
    )
    elem_dict: Optional[dict] = None
    if matches.get("found"):
        elem_dict = matches["elements"][0]
        detected = DetectedElement(
            name=elem_dict.get("name") or "",
            role=elem_dict.get("role") or "",
            automation_id=elem_dict.get("automation_id") or "",
        )
        result = get_uia_backend().expand_collapse_element(
            detected, action=action, window_title=window_title,
        )
        if result.get("success"):
            return _finish(result)

    from tools.spy_bridge import spy_expand_collapse_element
    spy = spy_expand_collapse_element(
        name=name,
        automation_id=automation_id,
        window_title=window_title,
        action=action,
    )
    if spy.get("success"):
        return _finish(spy)

    if not elem_dict and (automation_id or name):
        try:
            from tools.spy_bridge import spy_inspect_element, spy_props_to_element

            props = spy_inspect_element(
                name=name, automation_id=automation_id, window_title=window_title,
            )
            if props.get("found"):
                elem_dict = spy_props_to_element(
                    props.get("properties") or props, window_title=window_title,
                )
        except Exception:
            pass

    if fallback_click and elem_dict and _looks_like_uwp_expander(elem_dict):
        return _finish(_expand_element_fallback_header_click(elem_dict, window_title))

    err = spy.get("error", "Element not found or ExpandCollapse not supported")
    hint = None
    if elem_dict and _looks_like_uwp_expander(elem_dict):
        hint = "SettingsExpander has no ExpandCollapse — use fallback_click=true"
    out = {"success": False, "error": err, "code": "no_expand_pattern"}
    if hint:
        out["hint"] = hint
    return _finish(out)


def do_invoke_on_element(elem: dict, window_title: Optional[str] = None) -> dict:
    """Invoke via UIA using stored properties — no coordinate click."""
    if sys.platform != "win32":
        return {"success": False, "error": "invoke_element is Windows-only"}
    from detection.backends.uia_backend import get_uia_backend
    from detection.element_model import DetectedElement

    detected = DetectedElement(
        name=elem.get("name") or "",
        role=elem.get("role") or "",
        automation_id=elem.get("automation_id") or "",
    )
    return get_uia_backend().invoke_element(detected, window_title=window_title)


def _identifiable_by_properties(elem: dict) -> bool:
    return bool((elem.get("automation_id") or "").strip() or (elem.get("name") or "").strip())


def do_set_element_value(
    value: str,
    name: Optional[str] = None,
    automation_id: Optional[str] = None,
    window_title: Optional[str] = None,
    index: int = 0,
    window_handle: Optional[int] = None,
) -> dict:
    if sys.platform != "win32":
        return {"success": False, "error": "set_element_value is Windows-only"}
    from detection.backends.uia_backend import get_uia_backend
    from detection.element_model import DetectedElement
    matches = do_find_element(
        name=name,
        automation_id=automation_id,
        window_title=window_title,
        include_offscreen=True,
        index=0,
        window_handle=window_handle,
    )
    if not matches.get("found") or not matches.get("elements"):
        return {"success": False, "error": "Element not found"}
    idx = min(max(0, int(index or 0)), len(matches["elements"]) - 1)
    e = matches["elements"][idx]
    elem = DetectedElement(
        name=e["name"], role=e["role"], automation_id=e.get("automation_id", ""),
    )
    return get_uia_backend().set_element_value(elem, value, window_title=window_title)


def _fuzzy_find_nearest(
    name: Optional[str],
    role: Optional[str],
    window_title: Optional[str],
) -> Optional[dict]:
    all_result = do_list_elements(window_title=window_title, role=role)
    candidates = all_result.get("elements", [])
    if not candidates:
        return None

    best = None
    best_confidence = 0.0
    best_method = "none"

    for elem in candidates:
        confidence = 0.0
        method = "role_only"

        if name and elem.get("name"):
            ratio = SequenceMatcher(None, name.lower(), elem["name"].lower()).ratio()
            if ratio >= 0.6:
                confidence = 0.5 + (ratio * 0.4)
                method = "fuzzy_name"

        if confidence == 0.0 and role:
            confidence = 0.4
            method = "role_only"

        if confidence > best_confidence:
            best_confidence = confidence
            best = elem
            best_method = method

    if best is None:
        return None

    return {
        "element": best,
        "confidence": round(best_confidence, 2),
        "match_method": best_method,
    }


def _click_coords(elem: dict, window_title: Optional[str] = None) -> tuple[int, int]:
    from detection.element_coords import click_coords

    return click_coords(elem, window_title)


def _try_invoke_click(elem: dict, window_title: Optional[str] = None) -> Optional[dict]:
    """Use UIA Invoke when available — reliable for UWP/XAML buttons."""
    patterns = [str(p).lower() for p in (elem.get("patterns") or [])]
    role = (elem.get("role") or "").lower()
    if "invoke" not in patterns and role not in ("button", "hyperlink", "menuitem", "splitbutton"):
        return None
    inv = do_invoke_on_element(elem, window_title=window_title)
    return inv if inv.get("success") else None


def do_click_element(
    name: Optional[str] = None,
    role: Optional[str] = None,
    window_title: Optional[str] = None,
    index: int = 0,
    automation_id: Optional[str] = None,
    remember: bool = True,
    window_handle: Optional[int] = None,
    verify_automation_id: Optional[str] = None,
    verify_name_contains: Optional[str] = None,
    verify_timeout_ms: int = 5000,
    verify_poll_ms: int = 100,
    fuzzy_match: bool = False,
) -> dict:
    from tools.action_timing import ActionTimer
    from tools.app_session import normalize_index
    from tools.element_resolve import find_element_for_action

    verify_kwargs = {
        "verify_timeout_ms": verify_timeout_ms,
        "verify_poll_ms": verify_poll_ms,
    }

    timer = ActionTimer()
    timer.start("find")
    if fuzzy_match and (name or automation_id):
        elem, find_err = find_element_for_action(
            automation_id=automation_id,
            name=name,
            role=role,
            index=index,
            window_title=window_title,
            window_handle=window_handle,
            fuzzy_match=True,
        )
        if find_err:
            return timer.attach(find_err)
        result = {"found": True, "elements": [elem], "backend_used": "fuzzy"}
    else:
        result = do_find_element(
            name=name, role=role, window_title=window_title,
            index=index, automation_id=automation_id,
            remember=remember,
            window_handle=window_handle,
        )
    timer.end()
    if result["found"]:
        from tools.app_session import pick_element_index
        idx = pick_element_index(index, len(result["elements"]))
        elem = result["elements"][idx]
        timer.start("act")
        inv = _try_invoke_click(elem, window_title)
        timer.end()
        if inv:
            out = {
                "success": True,
                "element": elem,
                "method": inv.get("method", "InvokePattern"),
                "backend_used": result.get("backend_used", "uia"),
            }
            if result.get("repo_path"):
                out["repo_path"] = result["repo_path"]
            if result.get("method"):
                out["resolved_via"] = result["method"]
            return _finish_action_with_verify(
                timer,
                out,
                window_title=window_title,
                verify_automation_id=verify_automation_id,
                verify_name_contains=verify_name_contains,
                acted_automation_id=automation_id or elem.get("automation_id"),
                **verify_kwargs,
            )
        if _identifiable_by_properties(elem):
            out = {
                "success": False,
                "error": (
                    "Element found by properties but InvokePattern failed; "
                    "coordinate click skipped for identifiable controls"
                ),
                "element": elem,
                "repo_path": result.get("repo_path"),
            }
            return timer.attach(out)
        timer.start("act")
        center_x, center_y = _click_coords(elem, window_title)
        click_result = do_click(center_x, center_y)
        timer.end()
        out = {
            "success": True,
            "element": elem,
            "clicked_at": {"x": center_x, "y": center_y},
            "backend_used": result.get("backend_used", "uia"),
            "method": result.get("method", "click"),
        }
        if result.get("repo_path"):
            out["repo_path"] = result["repo_path"]
        if "navigation_warning" in click_result:
            out["navigation_warning"] = click_result["navigation_warning"]
        return _finish_action_with_verify(
            timer,
            out,
            window_title=window_title,
            verify_automation_id=verify_automation_id,
            verify_name_contains=verify_name_contains,
            acted_automation_id=automation_id,
            **verify_kwargs,
        )

    timer.start("find")
    nearest = _fuzzy_find_nearest(name=name, role=role, window_title=window_title)
    timer.end()
    if nearest is None:
        return timer.attach({"success": False, "error": f"Element not found: name={name}, role={role}"})

    if nearest["confidence"] >= 0.7:
        elem = nearest["element"]
        timer.start("act")
        center_x, center_y = _click_coords(elem, window_title)
        click_result = do_click(center_x, center_y)
        timer.end()
        out = {
            "success": True,
            "fallback": True,
            "confidence": nearest["confidence"],
            "match_method": nearest["match_method"],
            "element": elem,
            "clicked_at": {"x": center_x, "y": center_y},
            "note": (
                f"Exact match for '{name}' not found. Clicked nearest: "
                f"'{elem['name']}' ({nearest['match_method']}, confidence={nearest['confidence']})"
            ),
        }
        if "navigation_warning" in click_result:
            out["navigation_warning"] = click_result["navigation_warning"]
        return _finish_action_with_verify(
            timer,
            out,
            window_title=window_title,
            verify_automation_id=verify_automation_id,
            verify_name_contains=verify_name_contains,
            acted_automation_id=automation_id,
            **verify_kwargs,
        )

    elem = nearest["element"]
    cx, cy = _click_coords(elem, window_title)
    return timer.attach({
        "success": False,
        "nearest": {
            "element": elem,
            "confidence": nearest["confidence"],
            "match_method": nearest["match_method"],
        },
        "error": (
            f"Exact match for '{name}' not found. "
            f"Nearest: '{elem['name']}' ({nearest['match_method']}, confidence={nearest['confidence']}). "
            f"Confidence too low to auto-click (threshold=0.7). "
            f"Click at ({cx}, {cy}) to target it manually."
        ),
    })


def do_get_focused_element() -> dict:
    if sys.platform == "darwin":
        from awdui_platform.darwin_backend import ax_get_focused_element
        return ax_get_focused_element()

    err = ""
    try:
        from pywinauto import Desktop
        desktop = Desktop(backend="uia")
        focused = desktop.get_focus()
        from detection.backends.uia_backend import _pywinauto_to_element
        elem = _pywinauto_to_element(focused)
        if elem:
            return {"found": True, "element": _legacy_element(elem.to_dict())}
        return {"found": False, "error": "Focused element has no accessible info"}
    except Exception as e:
        err = str(e)

    # Fallback: UIA GetFocusedElement when pywinauto Desktop.get_focus() fails.
    try:
        from pywinauto.uia_defines import IUIA
        from pywinauto.controls.uiawrapper import UIAWrapper
        from pywinauto.uia_element_info import UIAElementInfo
        from detection.backends.uia_backend import _pywinauto_to_element

        raw = IUIA().iuia.GetFocusedElement()
        if raw:
            wrapper = UIAWrapper(UIAElementInfo(raw))
            elem = _pywinauto_to_element(wrapper)
            if elem:
                return {"found": True, "element": _legacy_element(elem.to_dict())}
    except Exception as fallback_err:
        err = err or str(fallback_err)

    return {"found": False, "error": err or "Cannot get focused element"}


def do_smart_find(
    name: str,
    role: Optional[str] = None,
    window_title: Optional[str] = None,
    index: int = 0,
    repo_path: Optional[str] = None,
    agentic: bool = False,
    remember: bool = True,
    remember_snapshot: bool = False,
    highlight: bool = False,
) -> dict:
    if sys.platform == "darwin":
        try:
            uia_result = do_find_element(name=name, role=role, window_title=window_title, index=index)
            if uia_result.get("found") and uia_result["elements"]:
                return {"found": True, "method": "ax", "elements": uia_result["elements"]}
        except Exception:
            pass
        try:
            from tools.ocr import do_find_text
            ocr_result = do_find_text(name, window_title=window_title)
            if ocr_result["matches"]:
                elements = [{
                    "name": m["text"], "role": "text",
                    "x": m["x"], "y": m["y"],
                    "width": m["width"], "height": m["height"],
                    "value": "", "backend": "ocr",
                } for m in ocr_result["matches"]]
                return {"found": True, "method": "ocr", "elements": elements}
        except Exception:
            pass
        return {"found": False, "elements": [], "error": f"'{name}' not found"}

    return _orch().smart_find(
        name=name,
        role=role,
        window_title=window_title,
        index=index,
        repo_path=repo_path,
        agentic=agentic,
        remember=remember,
        remember_snapshot=remember_snapshot,
        highlight=highlight,
    )


def do_repo_find(
    repo_path: str,
    window_title: Optional[str] = None,
    highlight: bool = False,
) -> dict:
    from tools.repo_action import do_repo_resolve
    result = do_repo_resolve(repo_path, window_title)
    if not result.get("found"):
        return {"found": False, "elements": [], "error": result.get("error", "not found")}
    elem = result["element"]
    out = {
        "found": True,
        "method": result.get("method", "repository"),
        "layer": "repository",
        "elements": [elem],
        "swf_class": result.get("swf_class"),
        "repo_path": repo_path,
    }
    if highlight:
        try:
            from tools.highlight import highlight_element_dict
            highlight_element_dict(elem)
        except Exception:
            pass
    return out


def do_repo_list(window_title: Optional[str] = None) -> dict:
    from detection.object_repository import list_objects, load_repo
    from detection.app_identity import repository_app_name
    from tools.framework_detect import do_detect_framework
    fw = do_detect_framework(window_title)
    app_name, exe_path = repository_app_name(fw, window_title)
    repo = load_repo(app_name, exe_path)
    win_key = None
    if window_title:
        for k, w in repo.get("windows", {}).items():
            if window_title.lower() in k.lower():
                win_key = k
                break
    return {"objects": list_objects(repo, win_key), "app_id": repo["app_id"]}


def do_build_detection_context(name: str = "", window_title: Optional[str] = None) -> dict:
    if sys.platform == "darwin":
        return {"error": "agentic context is Windows-only for now"}
    return _orch().build_detection_context(name=name, window_title=window_title)


def do_ui_fingerprint(
    window_title: Optional[str] = None,
    max_elements: int = 20,
) -> dict:
    result = do_list_elements(window_title=window_title, max_depth=3)
    elements = result.get("elements", [])[:max_elements]

    parts = []
    for elem in elements:
        parts.append(f"{elem.get('role', '')}|{elem.get('name', '')}|{elem['x']}|{elem['y']}")
    fingerprint_str = "\n".join(sorted(parts))

    hash_hex = hashlib.sha256(fingerprint_str.encode()).hexdigest()[:16]
    return {
        "hash": hash_hex,
        "element_count": len(elements),
    }


def do_detection_health(window_title: Optional[str] = None) -> dict:
    if sys.platform == "darwin":
        return {"backends": {"ax": {"available": True}}, "framework": "darwin"}
    return _orch().detection_health(window_title)


def register(server) -> int:
    """Register UI automation and inspector tools."""
    from tools.safety import with_timeout, ActionTimeoutError
    from tools.params import resolve_window_title as _wt

    @server.tool()
    def find_element(
        name: str = "",
        role: str = "",
        window_title: str = "",
        title: str = "",
        index: int = 0,
        automation_id: str = "",
        class_name: str = "",
        tree_mode: str = "control",
        include_offscreen: bool = False,
        window_handle: int = 0,
    ) -> str:
        """Find a UI element by name, role, automation_id, or class_name.

        Parameters:
            name: Text label (partial, case-insensitive).
            role: Control type -- Button, Edit, MenuItem, etc.
            window_title: Partial title of target window (default: foreground).
            window_handle: HWND of modal/child window (overrides title scope).
            index: Which match to return if multiple (0 = first).
            automation_id: WPF/UWP AutomationId (exact match).
            class_name: Win32 class name (partial match).
            tree_mode: UIA tree view -- control, raw, or content.
            include_offscreen: Include off-screen elements.
        """
        try:
            result = with_timeout(
                lambda: do_find_element(
                    name=name or None,
                    role=role or None,
                    window_title=_wt(window_title, title),
                    index=index,
                    automation_id=automation_id or None,
                    class_name=class_name or None,
                    tree_mode=tree_mode or "control",
                    include_offscreen=include_offscreen,
                    window_handle=window_handle or None,
                ),
                timeout=10.0,
            )
        except ActionTimeoutError:
            return f"Timed out after 10s searching for element name='{name}', role='{role}'."
        if not result["found"]:
            timing = ""
            try:
                from tools.action_timing import format_timing_suffix
                timing = format_timing_suffix(result)
            except Exception:
                pass
            return (
                f"No element found matching name='{name}', role='{role}', "
                f"automation_id='{automation_id}'. Error: {result.get('error', 'none')}{timing}"
            )

        backend = result.get("backend_used", "uia")
        lines = [f"Found {len(result['elements'])} matching element(s) via {backend}:"]
        for i, elem in enumerate(result["elements"]):
            aid = f" id={elem['automation_id']}" if elem.get("automation_id") else ""
            lines.append(
                f"[{i}] {elem['role']} \"{elem['name']}\"{aid} "
                f"({elem['x']},{elem['y']}) {elem['width']}x{elem['height']}"
            )
        try:
            from tools.action_timing import format_timing_suffix
            suffix = format_timing_suffix(result)
            if suffix:
                lines.append(suffix.strip())
        except Exception:
            pass
        return "\n".join(lines)

    @server.tool()
    def click_element(
        name: str = "",
        role: str = "",
        window_title: str = "",
        title: str = "",
        index: int = 0,
        automation_id: str = "",
        window_handle: int = 0,
        app_id: str = "",
        fuzzy_match: bool = False,
        capture: bool = False,
        capture_full: bool = False,
        verify_automation_id: str = "",
        verify_name_contains: str = "",
        verify_timeout_ms: int = 5000,
        verify_poll_ms: int = 100,
    ) -> list:
        """Find a UI element and click its center (or clickable point).

        Parameters:
            app_id: Optional WinApp-style session id from launch_app/attach_to_*.
            fuzzy_match: Tolerate typos/partial names when locating the element.
            capture: When True, attach a post-click screenshot (default False).
            capture_full: When True with capture, full screen; else target window if set.
            verify_automation_id: After click, poll until this control is found / matches.
            verify_name_contains: After click, poll until element name contains this text.
            verify_timeout_ms: Max wait for verify poll (default 5000).
            verify_poll_ms: Poll interval for verify (default 100).
        """
        from tools.params import resolve_scoped_window

        wt, hwnd, scope_err = resolve_scoped_window(
            app_id, window_title, title, window_handle,
        )
        if scope_err:
            return f"Failed: {scope_err}"
        action_timeout = 10.0
        if verify_automation_id or verify_name_contains:
            action_timeout = max(action_timeout, verify_timeout_ms / 1000.0 + 5.0)
        try:
            result = with_timeout(
                lambda: do_click_element(
                    name=name or None,
                    role=role or None,
                    window_title=wt,
                    index=index,
                    automation_id=automation_id or None,
                    window_handle=hwnd,
                    fuzzy_match=fuzzy_match,
                    verify_automation_id=verify_automation_id or None,
                    verify_name_contains=verify_name_contains or None,
                    verify_timeout_ms=verify_timeout_ms,
                    verify_poll_ms=verify_poll_ms,
                ),
                timeout=action_timeout,
            )
        except ActionTimeoutError:
            return f"Timed out after 10s trying to click element name='{name}'."
        if not result["success"]:
            error = result["error"]
            if "nearest" in result:
                n = result["nearest"]
                error += (
                    f"\nNearest candidate: {n['element']['role']} \"{n['element']['name']}\" "
                    f"(confidence={n['confidence']})"
                )
            return f"Failed: {error}"

        from tools.screenshot import action_tool_response
        elem = result["element"]
        method = result.get("method", result.get("backend_used", "uia"))
        if result.get("clicked_at"):
            at = result["clicked_at"]
            msg = (
                f"Clicked {elem['role']} \"{elem['name']}\" at "
                f"({at['x']}, {at['y']}) via {method}."
            )
        else:
            msg = (
                f"Activated {elem['role']} \"{elem['name']}\" "
                f"via {method}."
            )
        if result.get("fallback"):
            msg += f"\nFALLBACK: {result['note']}"
        if result.get("navigation_warning"):
            msg += f"\n⚠️ {result['navigation_warning']}"
        try:
            from tools.action_timing import format_timing_suffix, format_verify_suffix
            msg += format_timing_suffix(result) + format_verify_suffix(result)
        except Exception:
            pass
        return action_tool_response(msg, capture=capture, capture_full=capture_full)

    @server.tool()
    def list_elements(
        window_title: str = "",
        title: str = "",
        max_depth: int = 0,
        role: str = "",
        tree_mode: str = "control",
        include_offscreen: bool = False,
        window_handle: int = 0,
        adaptive_cluster: bool = True,
    ) -> str:
        """List accessible UI elements in a window.

        max_depth=0 (default) uses framework-adaptive depth (detect_framework).
        Use max_depth=-1 for unlimited, or N>0 for an explicit cap.
        adaptive_cluster=true (default) drops spatial outliers outside the dominant control band.
        include_offscreen=true includes collapsed/offscreen nodes.
        """
        try:
            result = with_timeout(
                lambda: do_list_elements(
                    window_title=_wt(window_title, title),
                    max_depth=max_depth,
                    role=role or None,
                    tree_mode=tree_mode or "control",
                    include_offscreen=include_offscreen,
                    window_handle=window_handle or None,
                    adaptive_cluster=adaptive_cluster,
                ),
                timeout=10.0,
            )
        except ActionTimeoutError:
            return "Timed out after 10s listing UI elements."
        if not result["elements"]:
            msg = f"No elements found. {result.get('error', '')}".strip()
            fw = do_detection_health(_wt(window_title, title)).get("framework")
            if fw in ("uwp", "winui"):
                msg += " UWP/WinUI: try smart_find or find_text/click_text (OCR) for button labels."
            return msg

        backend = result.get("backend_used", "uia")
        header = f"Found {result['count']} elements via {backend}"
        scoped_out = int(result.get("scoped_out") or 0)
        if scoped_out:
            header += f" ({scoped_out} out-of-scope removed)"
        cluster_out = int(result.get("cluster_out") or 0)
        if cluster_out:
            header += f" ({cluster_out} cluster-outliers removed)"
        region = result.get("content_region")
        if region and isinstance(region, dict):
            header += (
                f" content={region.get('w')}x{region.get('h')}"
                f"@{region.get('x')},{region.get('y')}"
            )
        req = result.get("max_depth_requested")
        eff = result.get("max_depth_effective")
        fw = result.get("framework_depth") or ""
        if req is not None:
            from detection.tree_depth import format_depth_header

            header += f" ({format_depth_header(int(req), int(eff or 0), str(fw))})"
        if role:
            header += f" with role '{role}'"
        header += ":"
        lines = [header]
        for i, elem in enumerate(result["elements"]):
            if not elem.get("name") and elem.get("role") in ("Pane", "Group", "Custom"):
                if not elem.get("automation_id") and not elem.get("class_name"):
                    continue
            name_str = f"\"{elem['name']}\"" if elem.get("name") else "(unnamed)"
            aid = f" id={elem['automation_id']}" if elem.get("automation_id") else ""
            lines.append(
                f"[{i}] {elem['role']} {name_str}{aid} "
                f"({elem['x']},{elem['y']}) {elem['width']}x{elem['height']}"
            )
            if i >= 100:
                lines.append(f"... and {result['count'] - 100} more (use role filter to narrow)")
                break
        try:
            from tools.action_timing import format_timing_suffix
            suffix = format_timing_suffix(result)
            if suffix:
                lines.append(suffix.strip())
        except Exception:
            pass
        return "\n".join(lines)

    @server.tool()
    def get_focused_element() -> str:
        """Get the currently focused UI element."""
        try:
            result = with_timeout(do_get_focused_element, timeout=5.0)
        except ActionTimeoutError:
            return "Timed out after 5s getting focused element."
        if not result["found"]:
            return f"Focus info unavailable. {result.get('error', '')}"
        e = result["element"]
        value_str = f" value=\"{e['value']}\"" if e.get("value") else ""
        return (
            f"Focused: {e['role']} \"{e['name']}\"{value_str} "
            f"at ({e['x']},{e['y']}) {e['width']}x{e['height']}"
        )

    @server.tool()
    def smart_find(
        name: str,
        role: str = "",
        window_title: str = "",
        title: str = "",
        index: int = 0,
        repo_path: str = "",
        agentic: bool = False,
        highlight: bool = False,
    ) -> str:
        """Find element via layered cascade: repo -> native -> OCR dual -> visual -> agentic."""
        try:
            result = with_timeout(
                lambda: do_smart_find(
                    name=name,
                    role=role or None,
                    window_title=_wt(window_title, title),
                    index=index,
                    repo_path=repo_path or None,
                    agentic=agentic,
                    highlight=highlight,
                ),
                timeout=20.0,
            )
        except ActionTimeoutError:
            return f"Timed out after 20s searching for '{name}'."
        if not result["found"]:
            if result.get("agentic_context"):
                ctx = result["agentic_context"]
                lines = [f"Not found via layers. Agentic context for '{name}':",
                           f"Tree sample: {ctx.get('element_count', 0)} elements",
                           ctx.get("visual_regions", "")]
                for act in ctx.get("suggested_actions", [])[:5]:
                    lines.append(f"  → {act}")
                return "\n".join(lines)
            return f"Not found: {result.get('error', 'unknown')}"

        method = result.get("method") or result.get("layer", "")
        lines = [f"Found {len(result['elements'])} match(es) via {method}:"]
        if result.get("repo_updated"):
            lines.append("(object repository updated)")
        for i, elem in enumerate(result["elements"]):
            lines.append(
                f"[{i}] {elem['role']} \"{elem['name']}\" "
                f"({elem['x']},{elem['y']}) {elem['width']}x{elem['height']}"
            )
        return "\n".join(lines)

    @server.tool()
    def ui_fingerprint(window_title: str = "", title: str = "") -> str:
        """Quick hash of the current UI layout for change detection."""
        try:
            result = with_timeout(
                lambda: do_ui_fingerprint(window_title=_wt(window_title, title)),
                timeout=5.0,
            )
        except ActionTimeoutError:
            return "Timed out computing UI fingerprint."
        return f"UI fingerprint: {result['hash']} ({result['element_count']} elements)"

    @server.tool()
    def element_at_point(x: int, y: int) -> str:
        """Get the UI element at screen coordinates (like Automation Spy pick)."""
        try:
            result = with_timeout(lambda: do_element_at_point(x, y), timeout=5.0)
        except ActionTimeoutError:
            return "Timed out."
        if not result.get("found"):
            return f"No element at ({x}, {y}). {result.get('error', '')}"
        e = result["element"]
        return (
            f"{e['role']} \"{e['name']}\" via {result.get('backend_used', 'uia')} "
            f"at ({e['x']},{e['y']}) {e['width']}x{e['height']}"
            + (f" automation_id={e['automation_id']}" if e.get("automation_id") else "")
        )

    @server.tool()
    def get_element_properties(
        name: str = "",
        automation_id: str = "",
        x: int = -1,
        y: int = -1,
        window_title: str = "",
        title: str = "",
    ) -> str:
        """Get full UIA properties for an element (Automation Spy style inspector)."""
        try:
            result = with_timeout(
                lambda: do_get_element_properties(
                    name=name or None,
                    automation_id=automation_id or None,
                    x=x if x >= 0 else None,
                    y=y if y >= 0 else None,
                    window_title=_wt(window_title, title),
                ),
                timeout=10.0,
            )
        except ActionTimeoutError:
            return "Timed out."
        if not result.get("found"):
            return f"Not found. {result.get('error', '')}"
        props = result["properties"]
        lines = [f"Properties via {result.get('backend_used', 'uia')}:"]
        for k, v in sorted(props.items()):
            if k != "raw_properties" and v not in ("", None, [], {}):
                lines.append(f"  {k}: {v}")
        return "\n".join(lines)

    @server.tool()
    def invoke_element(
        name: str = "",
        automation_id: str = "",
        window_title: str = "",
        title: str = "",
        verify_automation_id: str = "",
        verify_name_contains: str = "",
        verify_timeout_ms: int = 5000,
        verify_poll_ms: int = 100,
    ) -> str:
        """Invoke a button/menu via UIA patterns (Invoke, SelectionItem, Toggle, Expand).

        Returns phased timing: probe / find / act / verify. verify_* polls UIA until match
        (default 5s) — prefer over a separate wait_for_condition call.
        """
        action_timeout = 10.0
        if verify_automation_id or verify_name_contains:
            action_timeout = max(action_timeout, verify_timeout_ms / 1000.0 + 5.0)
        try:
            result = with_timeout(
                lambda: do_invoke_element(
                    name=name or None,
                    automation_id=automation_id or None,
                    window_title=_wt(window_title, title),
                    verify_automation_id=verify_automation_id or None,
                    verify_name_contains=verify_name_contains or None,
                    verify_timeout_ms=verify_timeout_ms,
                    verify_poll_ms=verify_poll_ms,
                ),
                timeout=action_timeout,
            )
        except ActionTimeoutError:
            return "Timed out."
        from tools.action_timing import format_timing_suffix, format_verify_suffix
        timing = format_timing_suffix(result)
        verify = format_verify_suffix(result)
        if result.get("success"):
            return f"Invoked via {result.get('method', 'InvokePattern')}{timing}{verify}"
        code = result.get("code")
        prefix = f"Failed ({code})" if code else "Failed"
        hint = result.get("hint")
        msg = f"{prefix}: {result.get('error', 'unknown')}{timing}"
        if hint:
            msg += f" — {hint}"
        return msg

    @server.tool()
    def expand_element(
        name: str = "",
        automation_id: str = "",
        window_title: str = "",
        title: str = "",
        action: str = "expand",
        fallback_click: bool = False,
    ) -> str:
        """Expand or collapse via ExpandCollapsePattern; fallback_click for UWP SettingsExpander."""
        try:
            result = with_timeout(
                lambda: do_expand_element(
                    name=name or None,
                    automation_id=automation_id or None,
                    window_title=_wt(window_title, title),
                    action=action or "expand",
                    fallback_click=bool(fallback_click),
                ),
                timeout=10.0,
            )
        except ActionTimeoutError:
            return "Timed out."
        if result.get("success"):
            from tools.action_timing import format_timing_suffix
            timing = format_timing_suffix(result)
            verb = "Collapsed" if (action or "expand").lower() == "collapse" else "Expanded"
            method = result.get("method", "ExpandCollapse")
            fb = " (header click)" if result.get("used_fallback_click") else ""
            fp = " fast-path" if result.get("fast_path") else ""
            return f"{verb} via {method}{fb}{fp}{timing}"
        hint = result.get("hint")
        msg = f"Failed: {result.get('error', 'unknown')}"
        if hint:
            msg += f" — {hint}"
        return msg

    @server.tool()
    def set_element_value(
        value: str,
        name: str = "",
        automation_id: str = "",
        window_title: str = "",
        title: str = "",
        index: int = 0,
        window_handle: int = 0,
    ) -> str:
        """Set text field value via UIA ValuePattern."""
        try:
            result = with_timeout(
                lambda: do_set_element_value(
                    value=value,
                    name=name or None,
                    automation_id=automation_id or None,
                    window_title=_wt(window_title, title),
                    index=index,
                    window_handle=window_handle or None,
                ),
                timeout=10.0,
            )
        except ActionTimeoutError:
            return "Timed out."
        if result.get("success"):
            return f"Value set via {result.get('method', 'ValuePattern')}"
        return f"Failed: {result.get('error', 'unknown')}"

    @server.tool()
    def detection_health(window_title: str = "", title: str = "") -> str:
        """Report which detection backends are available and element counts."""
        try:
            result = with_timeout(
                lambda: do_detection_health(window_title=_wt(window_title, title)),
                timeout=15.0,
            )
        except ActionTimeoutError:
            return "Timed out."
        lines = [f"Framework: {result.get('framework', 'unknown')}"]
        lines.append(f"Recommended order: {', '.join(result.get('recommended_order', []))}")
        for name, info in result.get("backends", {}).items():
            status = "OK" if info.get("available") else "unavailable"
            count = info.get("element_count", "?")
            lines.append(f"  {name}: {status} ({count} elements)")
        return "\n".join(lines)

    @server.tool()
    def check_java_bridge() -> str:
        """Check Java Access Bridge prerequisites for Swing/AWT automation."""
        try:
            from detection.backends.jab_backend import check_java_bridge
            result = check_java_bridge()
        except ImportError:
            return "pyjab not installed. pip install pyjab for Java support."
        lines = [
            f"JAB available: {result.get('available', False)}",
            f"JAVA_HOME: {result.get('java_home') or '(not set)'}",
            f"pyjab installed: {result.get('pyjab_installed', False)}",
        ]
        for hint in result.get("hints", []):
            lines.append(f"  → {hint}")
        return "\n".join(lines)

    @server.tool()
    def detect_visual_regions(window_title: str = "", title: str = "") -> str:
        """Detect clickable UI regions via OpenCV + OCR (for opaque apps)."""
        from tools.screenshot import capture_screenshot
        from tools.visual_detect import detect_ui_regions, format_regions_text
        from tools.image_utils import load_image_from_screenshot
        wt = _wt(window_title, title)
        if not wt:
            from tools.target_window import get_target
            wt = get_target()
        shot = capture_screenshot(window_title=wt)
        img = load_image_from_screenshot(shot)
        regions = detect_ui_regions(img, scale=1.0)
        return format_regions_text(regions)

    @server.tool()
    def repo_find(repo_path: str, window_title: str = "", title: str = "", highlight: bool = False) -> str:
        """Resolve a logical object from the UFT-style repository (e.g. frmMain/btnSave)."""
        try:
            result = with_timeout(
                lambda: do_repo_find(repo_path, window_title=_wt(window_title, title), highlight=highlight),
                timeout=20.0,
            )
        except ActionTimeoutError:
            return "Timed out."
        if not result.get("found"):
            return f"Not found: {result.get('error', '')}"
        e = result["elements"][0]
        swf = result.get("swf_class")
        swf_note = f" ({swf})" if swf else ""
        return (
            f"Resolved {repo_path}{swf_note} via {result.get('method', '')}: "
            f"{e['role']} \"{e['name']}\" at ({e['x']},{e['y']})"
        )

    @server.tool()
    def repo_list(window_title: str = "", title: str = "") -> str:
        """List objects stored in the repository for the active application."""
        result = do_repo_list(window_title=_wt(window_title, title))
        objs = result.get("objects", [])
        if not objs:
            return "Repository empty for this application."
        lines = [f"Repository ({result['app_id']}) — {len(objs)} object(s):"]
        for o in objs:
            cls = o.get("class", "control")
            parent = o.get("parent", "")
            parent_note = f" parent={parent}" if parent else ""
            lines.append(f"  {o['repo_path']} [{cls}]{parent_note}")
        return "\n".join(lines)

    @server.tool()
    def repo_hints(repo_path: str = "", window_title: str = "", title: str = "") -> str:
        """Get agent hints for a repository object or list hints for the active app.

        Parameters:
            repo_path: Full path (e.g. Calculadora/num6Button). If empty, lists objects with hints for the app.
            window_title: Application window context when repo_path is empty.
        """
        from detection import repo_store
        if repo_path:
            hints = repo_store.get_agent_hints(repo_path)
            if not hints:
                return f"No agent hints for '{repo_path}'."
            return f"Hints for {repo_path}:\n{hints}"
        result = do_repo_list(window_title=_wt(window_title, title))
        objs = result.get("objects", [])
        lines = []
        for o in objs:
            h = o.get("agent_hints") or repo_store.get_agent_hints(o["repo_path"])
            if h:
                lines.append(f"## {o['repo_path']}\n{h}")
        if not lines:
            return "No agent hints stored for this application."
        return "\n\n".join(lines)

    @server.tool()
    def repo_action(
        repo_path: str,
        method: str,
        value: str = "",
        property_name: str = "",
        window_title: str = "",
        title: str = "",
        highlight: bool = False,
    ) -> str:
        """Execute a QTP/UFT-style Swf* method on a repository object (e.g. Click, Set, Select)."""
        from tools.repo_action import do_repo_action
        try:
            result = with_timeout(
                lambda: do_repo_action(
                    repo_path=repo_path,
                    method=method,
                    value=value,
                    property_name=property_name,
                    window_title=_wt(window_title, title),
                    highlight=highlight,
                ),
                timeout=25.0,
            )
        except ActionTimeoutError:
            return f"Timed out executing {method} on '{repo_path}'."
        if not result.get("success"):
            err = result.get("error", "unknown")
            if result.get("allowed_methods"):
                err += f"\nAllowed for {result.get('swf_class')}: {', '.join(result['allowed_methods'])}"
            return f"Failed: {err}"
        msg = (
            f"{result.get('swf_class', 'SwfObject')}.{method} on '{repo_path}' OK "
            f"(resolved via {result.get('resolved_via', '')})"
        )
        if result.get("repo_updated"):
            msg += " [repo updated]"
        if result.get("value_set") == "****":
            msg += " [secure value]"
        elif result.get("typed"):
            msg += f" typed='{result['typed']}'"
        elif result.get("selected"):
            msg += f" selected='{result['selected']}'"
        elif result.get("text"):
            msg += f" text='{result['text']}'"
        elif result.get("value") is not None and method == "GetROProperty":
            msg += f" {result.get('property')}='{result['value']}'"
        return msg

    @server.tool()
    def repo_capture(
        repo_path: str,
        window_title: str = "",
        title: str = "",
        x: int = -1,
        y: int = -1,
        name: str = "",
        automation_id: str = "",
        parent: str = "",
    ) -> str:
        """Capture a control into the repository with Swf* class and Smart ID properties (Object Spy style)."""
        from tools.repo_action import do_repo_capture
        try:
            result = with_timeout(
                lambda: do_repo_capture(
                    repo_path=repo_path,
                    window_title=_wt(window_title, title),
                    x=x,
                    y=y,
                    name=name or "",
                    automation_id=automation_id or "",
                    parent=parent or "",
                ),
                timeout=20.0,
            )
        except ActionTimeoutError:
            return f"Timed out capturing '{repo_path}'."
        if not result.get("success"):
            return f"Capture failed: {result.get('error', '')}"
        methods = ", ".join(result.get("allowed_methods", []))
        return (
            f"Captured {result['repo_path']} as {result['swf_class']}. "
            f"Methods: {methods}"
        )

    @server.tool()
    def highlight_element(
        name: str = "",
        automation_id: str = "",
        repo_path: str = "",
        x: int = -1,
        y: int = -1,
        window_title: str = "",
        title: str = "",
        duration_ms: int = 3000,
    ) -> str:
        """Highlight an element on screen with a red border (Automation Spy style)."""
        from tools.highlight import highlight_element_dict, highlight_rect
        elem = None
        if repo_path:
            r = do_repo_find(repo_path, window_title=_wt(window_title, title))
            if r.get("found"):
                elem = r["elements"][0]
        elif name or automation_id:
            r = do_find_element(name=name or None, automation_id=automation_id or None,
                                window_title=_wt(window_title, title))
            if r.get("found"):
                elem = r["elements"][0]
        if elem:
            result = highlight_element_dict(
                elem,
                duration_ms=duration_ms,
                window_title=_wt(window_title, title),
                repo_path=repo_path,
            )
            return f"Highlighted {elem.get('name', repo_path)}: {result}"
        if x >= 0 and y >= 0:
            result = highlight_rect(x, y, 40, 24, duration_ms=duration_ms)
            return f"Highlighted point ({x},{y}): {result}"
        return "Provide repo_path, name/automation_id, or x/y."

    @server.tool()
    def clear_highlight() -> str:
        """Remove on-screen highlight overlays."""
        from tools.highlight import clear_highlight
        return str(clear_highlight())

    @server.tool()
    def discover_control_interaction(
        name: str = "",
        automation_id: str = "",
        window_title: str = "",
        title: str = "",
        x: int = -1,
        y: int = -1,
        include_children: bool = True,
    ) -> str:
        """Recommend MCP tools and steps from UIA role/patterns (generic, any app).

        Inspect the control (and optional children for Pane/Custom) and return
        ordered strategies: invoke_element, expand_element, set_element_value, etc.
        App-specific overrides come from repo agent_hints, not hardcoded rules.

        Parameters:
            automation_id: Preferred locator (WPF/UWP AutomationId).
            name: Partial control name if no automation_id.
            x, y: Point inspection instead of search.
            include_children: For containers, scan shallow children inside bbox.
        """
        try:
            result = with_timeout(
                lambda: do_discover_control_interaction(
                    name=name or None,
                    automation_id=automation_id or None,
                    window_title=_wt(window_title, title),
                    x=x if x >= 0 else None,
                    y=y if y >= 0 else None,
                    include_children=include_children,
                ),
                timeout=15.0,
            )
        except ActionTimeoutError:
            return "Timed out discovering control interaction."
        if not result.get("success"):
            return result.get("report_text") or result.get("error", "discovery failed")
        return result.get("report_text", "")

    @server.tool()
    def list_control_items(
        automation_id: str = "",
        filter_text: str = "",
        window_title: str = "",
        title: str = "",
        offset: int = 0,
        limit: int = 50,
        expand: bool = True,
    ) -> str:
        """List items under a ComboBox, List, or grid (paginated, scoped subtree).

        Expands ComboBox when expand=true. Falls back to Win32 ComboLBox enumeration
        for WinForms combos without UIA children. Use before select_control_item.
        """
        from tools.control_items import do_list_control_items

        if not automation_id:
            return "automation_id is required"
        try:
            result = with_timeout(
                lambda: do_list_control_items(
                    automation_id=automation_id,
                    filter_text=filter_text or "",
                    window_title=_wt(window_title, title),
                    offset=offset,
                    limit=limit,
                    expand=expand,
                ),
                timeout=20.0,
            )
        except ActionTimeoutError:
            return "Timed out listing control items."
        if not result.get("success"):
            return result.get("error", "list_control_items failed")
        lines = [
            f"source={result.get('source', 'uia')} matched={result.get('matched_total', 0)} "
            f"returned={result.get('returned', 0)} offset={result.get('offset', 0)} "
            f"has_more={result.get('has_more', False)}",
        ]
        for i, item in enumerate(result.get("items") or []):
            cells = item.get("cells")
            extra = f" cells={cells}" if cells else ""
            lines.append(
                f"  [{i}] {item.get('name', '')} ({item.get('x', 0)},{item.get('y', 0)})"
                f"{extra}"
            )
        return "\n".join(lines)

    @server.tool()
    def select_control_item(
        automation_id: str = "",
        value: str = "",
        window_title: str = "",
        title: str = "",
        double_click: bool = False,
        column: str = "",
    ) -> str:
        """Select a list/combo/grid item by substring match (never set_value on dropdown combos).

        ComboBox: expand + pick item + verify read-back. Grid/lookup: use double_click=true
        when the modal expects double-click to confirm. Returns requires_operation=click
        when WinForms ComboLBox needs an explicit click() at click_at.
        """
        from tools.control_items import do_select_control_item

        if not automation_id:
            return "automation_id is required"
        if not value:
            return "value is required"
        try:
            result = with_timeout(
                lambda: do_select_control_item(
                    automation_id=automation_id,
                    value=value,
                    window_title=_wt(window_title, title),
                    double_click=double_click,
                    column=column or "",
                ),
                timeout=20.0,
            )
        except ActionTimeoutError:
            return "Timed out selecting control item."
        if result.get("requires_operation") == "click":
            at = result.get("click_at") or {}
            return (
                f"requires_operation=click click_at=({at.get('x')},{at.get('y')}) "
                f"item={result.get('item', '')} — call click() at those coordinates"
            )
        if not result.get("success"):
            return result.get("error", "select_control_item failed")
        parts = [f"OK method={result.get('method', '')} selected={result.get('selected', value)}"]
        if result.get("verified_value"):
            parts.append(f"verified_value={result['verified_value']}")
        if result.get("warning"):
            parts.append(f"warning={result['warning']}")
        return " ".join(parts)

    @server.tool()
    def get_grid_item(
        automation_id: str = "",
        row: int = 0,
        column: int = 0,
        column_name: str = "",
        window_title: str = "",
        title: str = "",
    ) -> str:
        """Get a grid/table cell by row and column index (UIA GridPattern or DevExpress cells).

        Use for DataGrid/Table controls without walking the full tree. For DevExpress
        WinForms grids, column_name can name the column (e.g. titulo); otherwise column
        is a 0-based index over discovered column keys.
        """
        from tools.control_items import do_get_grid_item

        if not automation_id:
            return "automation_id is required"
        try:
            result = with_timeout(
                lambda: do_get_grid_item(
                    automation_id=automation_id,
                    row=row,
                    column=column,
                    column_name=column_name or "",
                    window_title=_wt(window_title, title),
                ),
                timeout=15.0,
            )
        except ActionTimeoutError:
            return "Timed out reading grid cell."
        if not result.get("success"):
            return result.get("error", "get_grid_item failed")
        return (
            f"OK row={result.get('row_index')} col={result.get('column_index')} "
            f"name={result.get('column_name', '')!r} value={result.get('value', '')!r} "
            f"source={result.get('source', '')} at ({result.get('x', 0)},{result.get('y', 0)})"
        )

    @server.tool()
    def read_table(
        automation_id: str = "",
        filter_text: str = "",
        window_title: str = "",
        title: str = "",
        offset: int = 0,
        limit: int = 200,
    ) -> str:
        """Read a grid/table as JSON {headers, rows} (UIA Grid/Table + DevExpress fallback).

        Rows are arrays aligned with headers. Paginate with offset/limit (max 500).
        """
        import json

        from tools.control_items import do_read_table

        if not automation_id:
            return "automation_id is required"
        try:
            result = with_timeout(
                lambda: do_read_table(
                    automation_id=automation_id,
                    filter_text=filter_text or "",
                    window_title=_wt(window_title, title),
                    offset=offset,
                    limit=limit,
                ),
                timeout=30.0,
            )
        except ActionTimeoutError:
            return "Timed out reading table."
        if not result.get("success"):
            return result.get("error", "read_table failed")
        payload = {
            "success": True,
            "automation_id": automation_id,
            "source": result.get("source", ""),
            "headers": result.get("headers") or [],
            "rows": result.get("rows") or [],
            "row_count": result.get("row_count", 0),
            "total_rows": result.get("total_rows", 0),
            "offset": result.get("offset", 0),
            "limit": result.get("limit", limit),
            "has_more": result.get("has_more", False),
        }
        return json.dumps(payload, ensure_ascii=False)

    @server.tool()
    def scroll_into_view(
        automation_id: str = "",
        name: str = "",
        role: str = "",
        index: int = -1,
        window_title: str = "",
        title: str = "",
        window_handle: int = 0,
        app_id: str = "",
    ) -> str:
        """Scroll a list/grid item into view via ScrollItemPattern.ScrollIntoView."""
        from tools.params import resolve_scoped_window
        from tools.uia_pattern_tools import do_scroll_into_view

        wt, hwnd, scope_err = resolve_scoped_window(app_id, window_title, title, window_handle)
        if scope_err:
            return scope_err
        if not (automation_id or name or role):
            return "automation_id, name, or role is required"
        try:
            result = with_timeout(
                lambda: do_scroll_into_view(
                    automation_id=automation_id,
                    name=name or None,
                    role=role or None,
                    index=index,
                    window_title=wt,
                    window_handle=hwnd,
                ),
                timeout=15.0,
            )
        except ActionTimeoutError:
            return "Timed out scrolling item into view."
        if not result.get("success"):
            return result.get("error", "scroll_into_view failed")
        return (
            f"OK method={result.get('method', '')} "
            f"name={result.get('name', '')!r} at ({result.get('x', 0)},{result.get('y', 0)})"
        )

    @server.tool()
    def realize_virtualized_item(
        automation_id: str = "",
        name: str = "",
        role: str = "",
        index: int = -1,
        window_title: str = "",
        title: str = "",
        window_handle: int = 0,
        app_id: str = "",
    ) -> str:
        """Materialize a virtualized list item via VirtualizedItemPattern.Realize."""
        from tools.params import resolve_scoped_window
        from tools.uia_pattern_tools import do_realize_virtualized_item

        wt, hwnd, scope_err = resolve_scoped_window(app_id, window_title, title, window_handle)
        if scope_err:
            return scope_err
        if not (automation_id or name or role):
            return "automation_id, name, or role is required"
        try:
            result = with_timeout(
                lambda: do_realize_virtualized_item(
                    automation_id=automation_id,
                    name=name or None,
                    role=role or None,
                    index=index,
                    window_title=wt,
                    window_handle=hwnd,
                ),
                timeout=15.0,
            )
        except ActionTimeoutError:
            return "Timed out realizing virtualized item."
        if not result.get("success"):
            return result.get("error", "realize_virtualized_item failed")
        return (
            f"OK method={result.get('method', '')} "
            f"name={result.get('name', '')!r} role={result.get('role', '')}"
        )

    @server.tool()
    def find_item_by_property(
        container_automation_id: str = "",
        property_name: str = "name",
        property_value: str = "",
        start_after_automation_id: str = "",
        window_title: str = "",
        title: str = "",
    ) -> str:
        """Find a child item in a list/tree via ItemContainer.FindItemByProperty (subtree fallback)."""
        from tools.uia_pattern_tools import do_find_item_by_property

        if not container_automation_id:
            return "container_automation_id is required"
        if not property_value:
            return "property_value is required"
        try:
            result = with_timeout(
                lambda: do_find_item_by_property(
                    container_automation_id=container_automation_id,
                    property_name=property_name or "name",
                    property_value=property_value,
                    start_after_automation_id=start_after_automation_id or "",
                    window_title=_wt(window_title, title),
                ),
                timeout=20.0,
            )
        except ActionTimeoutError:
            return "Timed out finding item by property."
        if not result.get("success"):
            return result.get("error", "find_item_by_property failed")
        return (
            f"OK method={result.get('method', '')} "
            f"{result.get('property', '')}={result.get('value', '')!r} "
            f"name={result.get('name', '')!r} automation_id={result.get('automation_id', '')!r}"
        )

    @server.tool()
    def scroll_element(
        automation_id: str = "",
        name: str = "",
        role: str = "",
        index: int = -1,
        direction: str = "down",
        amount: str = "large",
        repeat: int = 1,
        clicks: int = 0,
        horizontal_percent: float = -1.0,
        vertical_percent: float = -1.0,
        window_title: str = "",
        title: str = "",
        window_handle: int = 0,
        app_id: str = "",
    ) -> str:
        """Scroll a scrollable container via ScrollPattern (direction/amount or SetScrollPercent)."""
        from tools.params import resolve_scoped_window
        from tools.uia_pattern_tools import do_scroll_element

        wt, hwnd, scope_err = resolve_scoped_window(app_id, window_title, title, window_handle)
        if scope_err:
            return scope_err
        if not (automation_id or name or role):
            return "automation_id, name, or role is required"
        try:
            result = with_timeout(
                lambda: do_scroll_element(
                    automation_id=automation_id,
                    name=name or None,
                    role=role or None,
                    index=index,
                    direction=direction or "down",
                    amount=amount or "large",
                    repeat=repeat,
                    clicks=clicks,
                    horizontal_percent=horizontal_percent,
                    vertical_percent=vertical_percent,
                    window_title=wt,
                    window_handle=hwnd,
                ),
                timeout=15.0,
            )
        except ActionTimeoutError:
            return "Timed out scrolling element."
        if not result.get("success"):
            return result.get("error", "scroll_element failed")
        if result.get("method") == "Scroll.SetScrollPercent":
            return (
                f"OK method={result.get('method')} "
                f"h={result.get('horizontal_percent')} v={result.get('vertical_percent')}"
            )
        return (
            f"OK method={result.get('method', '')} direction={result.get('direction', '')} "
            f"amount={result.get('amount', '')} repeat={result.get('repeat', 1)}"
        )

    @server.tool()
    def spy_inspect(
        name: str = "",
        automation_id: str = "",
        x: int = -1,
        y: int = -1,
        window_title: str = "",
        title: str = "",
    ) -> str:
        """Spy-grade full UIA property inspection (40+ fields)."""
        from tools.spy_bridge import spy_inspect_at, spy_inspect_element, spy_available
        if not spy_available():
            return "spy sidecar not built. Run mcp-servers/awdui-spy-sidecar/build.cmd"
        if x >= 0 and y >= 0:
            result = spy_inspect_at(x, y)
        else:
            result = spy_inspect_element(name=name or None, automation_id=automation_id or None,
                                         window_title=_wt(window_title, title))
        if not result.get("found") and "properties" not in result:
            return f"Not found: {result.get('error', '')}"
        props = result.get("properties", result)
        lines = ["Spy inspection:"]
        for k, v in sorted(props.items()):
            if v not in ("", None, [], {}):
                lines.append(f"  {k}: {v}")
        return "\n".join(lines)

    @server.tool()
    def spy_tree(
        window_title: str = "",
        title: str = "",
        mode: str = "control",
        max_depth: int = 0,
        visible_only: bool = False,
    ) -> str:
        """Walk UIA tree with Spy-grade detail.

        max_depth=0 (default) = framework-adaptive depth. max_depth=-1 = unlimited.
        """
        from detection.tree_depth import SPY_TREE_DEFAULT_MAX_DEPTH, format_depth_header, resolve_list_depth
        from tools.spy_bridge import spy_tree, spy_available
        if not spy_available():
            return "spy sidecar not built."
        wt = _wt(window_title, title)
        requested, effective, fw = resolve_list_depth(
            max_depth if max_depth is not None else SPY_TREE_DEFAULT_MAX_DEPTH,
            window_title=wt or None,
        )
        result = spy_tree(
            wt,
            mode,
            effective,
            visible_only=visible_only,
        )
        elements = result.get("elements", [])
        depth_note = f" ({format_depth_header(requested, effective, fw)})"
        lines = [f"Spy tree: {result.get('count', len(elements))} elements{depth_note}"]
        for i, e in enumerate(elements[:50]):
            lines.append(f"  [{i}] {e.get('role')} \"{e.get('name')}\" id={e.get('automation_id', '')}")
        if len(elements) > 50:
            lines.append(f"  ... and {len(elements) - 50} more")
        return "\n".join(lines)

    @server.tool()
    def build_detection_context(name: str = "", window_title: str = "", title: str = "") -> str:
        """Rich agentic context: screenshot, tree, OCR dual, visual regions, suggestions."""
        try:
            ctx = with_timeout(
                lambda: do_build_detection_context(name, window_title=_wt(window_title, title)),
                timeout=25.0,
            )
        except ActionTimeoutError:
            return "Timed out building detection context."
        if ctx.get("error") and not ctx.get("screenshot_path"):
            return f"No context available: {ctx['error']}"
        if not ctx or not ctx.get("screenshot_path"):
            return "No context available."
        lines = [
            f"Detection context for '{name or '(all)'}':",
            f"Screenshot: {ctx.get('screenshot_path', '')}",
            f"Accessibility tree: {ctx.get('element_count', 0)} elements (sample below)",
        ]
        for e in ctx.get("tree_sample", [])[:10]:
            lines.append(f"  {e.get('role')} \"{e.get('name')}\"")
        lines.append(ctx.get("visual_regions", ""))
        lines.append("Suggested actions:")
        for act in ctx.get("suggested_actions", [])[:8]:
            lines.append(f"  {act}")
        return "\n".join(lines)

    return 26

"""QTP/UFT-style repository actions — Swf* methods on logical object names."""
from __future__ import annotations

import sys
from typing import Any, Optional

from detection.object_repository import load_repo, upsert_object
from detection.repo_resolver import identification_for_capture, resolve_repo_object
from detection.winforms_map import allowed_methods, infer_swf_class, validate_method


def _orch():
    from detection.orchestrator import get_orchestrator
    return get_orchestrator()


def _app_repo(window_title: Optional[str]) -> tuple[str, dict]:
    from tools.framework_detect import do_detect_framework
    fw = do_detect_framework(window_title)
    app_name = fw.get("process_name") or fw.get("exe_name") or "foreground"
    repo = load_repo(app_name, fw.get("exe_path", ""))
    repo["exe_path"] = fw.get("exe_path", "")
    repo["framework"] = fw.get("framework", repo.get("framework", "unknown"))
    return app_name, repo


def _template_matcher(template_rel: str, window_title: Optional[str]) -> Optional[dict]:
    from detection.layers.layered_detector import LayeredDetector
    det = LayeredDetector(_orch())
    return det._template_match(template_rel, window_title)


def _ocr_finder(text: str, window_title: Optional[str]) -> list[dict]:
    try:
        from tools.ocr import do_find_text_dual
        result = do_find_text_dual(text, window_title=window_title)
        return [{
            "name": m["text"],
            "role": "text",
            "x": m["x"], "y": m["y"],
            "width": m["width"], "height": m["height"],
            "value": "",
            "backend": m.get("engine", "ocr"),
        } for m in result.get("matches", [])]
    except Exception:
        return []


def do_repo_resolve(
    repo_path: str,
    window_title: Optional[str] = None,
) -> dict[str, Any]:
    if sys.platform == "darwin":
        return {"found": False, "error": "repo resolution is Windows-only for now"}
    _, repo = _app_repo(window_title)
    return resolve_repo_object(
        repo, repo_path, _orch(),
        window_title=window_title,
        template_matcher=_template_matcher,
        ocr_finder=_ocr_finder,
    )


def _click_coords(elem: dict, window_title: Optional[str] = None) -> tuple[int, int]:
    from detection.element_coords import click_coords

    return click_coords(elem, window_title)


def _select_uia(elem: dict, value: str, window_title: Optional[str]) -> dict:
    if sys.platform != "win32":
        return {"success": False, "error": "Select is Windows-only"}
    try:
        from detection.backends.uia_backend import UIABackend, _pywinauto_to_element
        from pywinauto.uia_defines import get_elem_interface

        backend = UIABackend()
        raw, _ = backend._find_raw_element(
            name=elem.get("name") or "",
            role=elem.get("role") or "",
            window_title=window_title,
        )
        if not raw:
            return {"success": False, "error": "Element not found for Select"}

        if elem.get("role") in ("ComboBox", "DropDown"):
            try:
                get_elem_interface(raw.element_info.element, "ExpandCollapse").Expand()
            except Exception:
                pass

        for child in raw.descendants():
            cd = _pywinauto_to_element(child)
            if not cd:
                continue
            if value.lower() in (cd.name or "").lower():
                try:
                    get_elem_interface(child.element_info.element, "SelectionItem").Select()
                    return {"success": True, "method": "SelectionItemPattern", "selected": cd.name}
                except Exception:
                    from tools.input_tools import do_click
                    cx, cy = cd.x + cd.width // 2, cd.y + cd.height // 2
                    do_click(cx, cy)
                    return {"success": True, "method": "click_item", "selected": cd.name}
        return {"success": False, "error": f"Item '{value}' not found in control"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _expand_collapse(elem: dict, window_title: Optional[str], expand: bool) -> dict:
    if sys.platform != "win32":
        return {"success": False, "error": "Expand/Collapse is Windows-only"}
    from detection.backends.uia_backend import UIABackend
    backend = UIABackend()
    fn = backend.expand_element if expand else backend.collapse_element
    return fn(
        name=elem.get("name", ""),
        role=elem.get("role", "TreeItem"),
        window_title=window_title,
    )


def _get_ro_property(elem: dict, prop: str, window_title: Optional[str]) -> dict:
    if prop in elem:
        return {"success": True, "property": prop, "value": elem[prop]}
    if sys.platform == "win32":
        from tools.ui_automation import do_get_element_properties
        result = do_get_element_properties(
            name=elem.get("name") or None,
            automation_id=elem.get("automation_id") or None,
            window_title=window_title,
        )
        if result.get("found"):
            props = result.get("properties", {})
            if prop in props:
                return {"success": True, "property": prop, "value": props[prop]}
            return {"success": True, "property": prop, "value": props.get(prop, "")}
    return {"success": False, "error": f"Property '{prop}' unavailable"}


def _get_visible_text(elem: dict, window_title: Optional[str]) -> dict:
    text = elem.get("value") or elem.get("name") or ""
    if text:
        return {"success": True, "text": text}
    try:
        from tools.ocr import run_dual_ocr
        x, y, w, h = elem["x"], elem["y"], elem["width"], elem["height"]
        from tools.screenshot import capture_screenshot
        from tools.image_utils import load_image_from_screenshot
        shot = capture_screenshot(window_title=window_title)
        img = load_image_from_screenshot(shot)
        crop = img.crop((x, y, x + w, y + h))
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        crop.save(tmp.name)
        words = " ".join(w["text"] for w in run_dual_ocr(tmp.name))
        if words:
            return {"success": True, "text": words}
    except Exception:
        pass
    return {"success": False, "error": "No visible text found"}


def do_repo_action(
    repo_path: str,
    method: str,
    value: str = "",
    window_title: Optional[str] = None,
    property_name: str = "",
    highlight: bool = False,
    remember: bool = True,
) -> dict[str, Any]:
    """Execute a QTP-style Swf* method on a repository object."""
    resolved = do_repo_resolve(repo_path, window_title)
    if not resolved.get("found"):
        return {"success": False, "error": resolved.get("error", "not found")}

    elem = resolved["element"]
    swf_class = resolved.get("swf_class", "SwfObject")
    err = validate_method(swf_class, method)
    if err:
        return {"success": False, "error": err, "swf_class": swf_class, "allowed_methods": allowed_methods(swf_class)}

    if highlight:
        try:
            from tools.highlight import highlight_element_dict
            highlight_element_dict(elem)
        except Exception:
            pass

    result: dict[str, Any] = {
        "success": False,
        "repo_path": repo_path,
        "swf_class": swf_class,
        "method": method,
        "resolved_via": resolved.get("method", ""),
    }

    if method == "Click":
        from tools.ui_automation import do_invoke_element
        inv = do_invoke_element(
            name=elem.get("name") or None,
            automation_id=elem.get("automation_id") or None,
            window_title=window_title,
        )
        if inv.get("success"):
            result.update({"success": True, "action": inv.get("method", "InvokePattern")})
        else:
            from tools.input_tools import do_click
            cx, cy = _click_coords(elem, window_title)
            do_click(cx, cy)
            result.update({"success": True, "action": "click", "clicked_at": {"x": cx, "y": cy}})

    elif method == "DblClick":
        from tools.input_tools import do_click
        cx, cy = _click_coords(elem, window_title)
        do_click(cx, cy, clicks=2)
        result.update({"success": True, "action": "dblclick", "clicked_at": {"x": cx, "y": cy}})

    elif method in ("Set", "SetSecure"):
        from tools.ui_automation import do_set_element_value
        set_result = do_set_element_value(
            value=value,
            name=elem.get("name") or None,
            automation_id=elem.get("automation_id") or None,
            window_title=window_title,
        )
        result.update(set_result)
        if method == "SetSecure":
            result["value_set"] = "****"

    elif method == "FireEvent":
        from tools.ui_automation import do_invoke_element
        result.update(do_invoke_element(
            name=elem.get("name") or None,
            automation_id=elem.get("automation_id") or None,
            window_title=window_title,
        ))

    elif method == "Select":
        if not value:
            return {"success": False, "error": "Select requires 'value' (item text)"}
        result.update(_select_uia(elem, value, window_title))

    elif method == "Deselect":
        result.update(_select_uia(elem, value or elem.get("name", ""), window_title))

    elif method == "Type":
        from tools.ui_automation import do_set_element_value
        from tools.input_tools import do_type_text
        set_result = do_set_element_value(
            value="",
            name=elem.get("name") or None,
            automation_id=elem.get("automation_id") or None,
            window_title=window_title,
        )
        if not set_result.get("success"):
            from tools.input_tools import do_click
            cx, cy = _click_coords(elem, window_title)
            do_click(cx, cy)
        do_type_text(value)
        result.update({"success": True, "action": "type", "typed": value})

    elif method == "Expand":
        result.update(_expand_collapse(elem, window_title, True))

    elif method == "Collapse":
        result.update(_expand_collapse(elem, window_title, False))

    elif method == "Highlight":
        from tools.highlight import highlight_element_dict
        result.update({"success": True, "highlight": highlight_element_dict(elem)})

    elif method == "GetROProperty":
        prop = property_name or value or "name"
        result.update(_get_ro_property(elem, prop, window_title))

    elif method == "GetVisibleText":
        result.update(_get_visible_text(elem, window_title))

    elif method == "SetSelection":
        if not value or "," not in value:
            return {"success": False, "error": "SetSelection requires value='start,end'"}
        start_s, end_s = value.split(",", 1)
        start, end = int(start_s.strip()), int(end_s.strip())
        from tools.input_tools import do_click, do_send_keys
        cx, cy = _click_coords(elem, window_title)
        do_click(cx, cy)
        do_send_keys("{HOME}")
        for _ in range(start):
            do_send_keys("{RIGHT}")
        for _ in range(max(0, end - start)):
            do_send_keys("+{RIGHT}")
        result.update({"success": True, "action": "SetSelection", "range": value})

    else:
        return {"success": False, "error": f"Method '{method}' not implemented"}

    if remember and result.get("success"):
        _, repo = _app_repo(window_title)
        from detection.object_repository import parse_repo_path
        window_key, chain = parse_repo_path(repo_path)
        meta = identification_for_capture(elem, swf_class, parent=chain[-2] if len(chain) > 1 else "")
        upsert_object(
            repo,
            repo_path,
            obj_class=swf_class,
            identification=meta["identification"],
            parent=meta["parent"],
            last_resolution={
                "layer": "repository",
                "backend": elem.get("backend_used", elem.get("backend", "uia")),
                "method": resolved.get("method", ""),
                "bbox": {
                    "x": elem.get("x", 0),
                    "y": elem.get("y", 0),
                    "w": elem.get("width", 0),
                    "h": elem.get("height", 0),
                },
            },
        )
        result["repo_updated"] = True

    return result


def do_repo_capture(
    repo_path: str,
    window_title: Optional[str] = None,
    x: int = -1,
    y: int = -1,
    name: str = "",
    automation_id: str = "",
    parent: str = "",
    highlight: bool = True,
) -> dict[str, Any]:
    """Capture a control into the repository (Object Spy → Add to Repository)."""
    elem: Optional[dict] = None
    if x >= 0 and y >= 0:
        from tools.spy_bridge import spy_inspect_at, spy_available
        if spy_available():
            spy = spy_inspect_at(x, y)
            if spy.get("properties"):
                props = spy["properties"]
                elem = {
                    "name": props.get("Name", props.get("name", "")),
                    "role": props.get("ControlType", props.get("role", "")),
                    "automation_id": props.get("AutomationId", props.get("automation_id", "")),
                    "class_name": props.get("ClassName", props.get("class_name", "")),
                    "x": props.get("x", x),
                    "y": props.get("y", y),
                    "width": props.get("width", 40),
                    "height": props.get("height", 24),
                    "value": props.get("Value", ""),
                    "backend": "uia",
                }
    if not elem and (name or automation_id):
        from tools.ui_automation import do_find_element
        found = do_find_element(name=name or None, automation_id=automation_id or None, window_title=window_title)
        if found.get("found"):
            elem = found["elements"][0]

    if not elem:
        return {"success": False, "error": "Provide x/y or name/automation_id to capture"}

    swf_class = infer_swf_class(elem.get("role", ""), elem.get("class_name", ""))
    _, repo = _app_repo(window_title)
    from detection.object_repository import parse_repo_path
    try:
        window_key, chain = parse_repo_path(repo_path)
    except ValueError as e:
        return {"success": False, "error": str(e)}
    if not parent and len(chain) > 1:
        parent = chain[-2]

    meta = identification_for_capture(elem, swf_class, parent=parent)
    upsert_object(
        repo,
        repo_path,
        obj_class=swf_class,
        identification=meta["identification"],
        parent=parent,
        element=elem,
    )

    if highlight:
        try:
            from tools.highlight import highlight_element_dict
            highlight_element_dict(elem)
        except Exception:
            pass

    try:
        from detection.object_snapshot import capture_object_snapshot
        capture_object_snapshot(
            elem,
            window_title=window_title,
            repo_path=repo_path,
            app_name=repo.get("app_name", "foreground"),
            exe_path="",
            highlight=False,
        )
    except Exception:
        pass

    return {
        "success": True,
        "repo_path": repo_path,
        "swf_class": swf_class,
        "identification": meta["identification"],
        "allowed_methods": meta["allowed_methods"],
    }

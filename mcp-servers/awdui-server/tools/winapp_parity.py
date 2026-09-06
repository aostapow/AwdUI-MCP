"""WinApp MCP parity tools — session registry, fuzzy find, HWND helpers, screenshots."""
from __future__ import annotations

import base64
import hashlib
import io
import sys
from pathlib import Path
from typing import Any, Optional

from tools.app_session import (
    filter_windows_for_app,
    list_registered_apps,
    pick_element_index as _resolve_index,
    register_window,
    resolve_scope as _resolve_scope,
)


def do_attach_to_app(process_name: str) -> dict[str, Any]:
    from tools.windows import do_list_windows

    needle = (process_name or "").strip().lower()
    if not needle:
        return {"success": False, "error": "process_name is required"}

    windows = do_list_windows()
    matches = [
        w
        for w in windows
        if needle in str(w.get("process") or "").lower()
        or needle in str(w.get("title") or "").lower()
    ]
    if not matches:
        return {"success": False, "error": f"No running window for '{process_name}'"}
    return register_window(matches[0])


def do_attach_to_pid(pid: int) -> dict[str, Any]:
    from tools.windows import do_list_windows

    if not pid:
        return {"success": False, "error": "pid is required"}
    windows = do_list_windows()
    matches = [w for w in windows if int(w.get("pid") or 0) == int(pid)]
    if not matches:
        return {"success": False, "error": f"No window for pid {pid}"}
    return register_window(matches[0])


def do_list_apps() -> dict[str, Any]:
    apps = []
    for app_id, meta in list_registered_apps().items():
        apps.append({"app_id": app_id, **meta})
    return {"success": True, "count": len(apps), "apps": apps}


def do_close_app(app_id: str) -> dict[str, Any]:
    from tools.app_session import get_app, unregister_app

    app = get_app(app_id)
    if not app:
        return {"success": False, "error": f"Unknown app_id: {app_id}"}
    pid = int(app.get("pid") or 0)
    if sys.platform == "win32" and pid:
        try:
            import ctypes

            PROCESS_TERMINATE = 0x0001
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
            if handle:
                ctypes.windll.kernel32.TerminateProcess(handle, 0)
                ctypes.windll.kernel32.CloseHandle(handle)
        except Exception as exc:
            return {"success": False, "error": str(exc)}
    unregister_app(app_id)
    return {"success": True, "closed": app_id, "pid": pid}


def do_list_desktop_windows() -> dict[str, Any]:
    from tools.windows import do_list_windows

    windows = do_list_windows()
    rows = []
    for w in windows:
        rows.append(
            {
                "hwnd": int(w.get("hwnd") or 0),
                "title": w.get("title", ""),
                "pid": int(w.get("pid") or 0),
                "process": w.get("process", ""),
                "x": w.get("x", 0),
                "y": w.get("y", 0),
                "width": w.get("width", 0),
                "height": w.get("height", 0),
            }
        )
    return {"success": True, "count": len(rows), "windows": rows}


def do_release_keyboard() -> dict[str, Any]:
    try:
        import pyautogui

        for key in ("shift", "ctrl", "alt", "win"):
            try:
                pyautogui.keyUp(key)
            except Exception:
                pass
    except Exception:
        pass
    return {"success": True, "released": True}


def do_find_elements(
    control_type: Optional[str] = None,
    id_contains: Optional[str] = None,
    name_contains: Optional[str] = None,
    max_results: int = 50,
    window_title: Optional[str] = None,
    window_handle: Optional[int] = None,
    app_id: str = "",
) -> dict[str, Any]:
    if sys.platform != "win32":
        return {"success": False, "error": "find_elements is Windows-only"}
    wt, hwnd, err = _resolve_scope(app_id, window_title)
    if err:
        return err
    hwnd = window_handle or hwnd

    from tools.ui_automation import do_list_elements

    listing = do_list_elements(
        window_title=wt or None,
        window_handle=hwnd,
        max_depth=8,
        include_offscreen=False,
    )
    results: list[dict[str, Any]] = []
    ct = (control_type or "").lower()
    id_q = (id_contains or "").lower()
    name_q = (name_contains or "").lower()

    for elem in listing.get("elements") or []:
        role = str(elem.get("role") or "")
        if ct and ct not in role.lower():
            continue
        aid = str(elem.get("automation_id") or "")
        name = str(elem.get("name") or "")
        if id_q and id_q not in aid.lower():
            continue
        if name_q and name_q not in name.lower():
            continue
        results.append(elem)
        if len(results) >= max(1, int(max_results or 50)):
            break

    return {
        "success": bool(results),
        "count": len(results),
        "elements": results,
        "backend_used": listing.get("backend_used", ""),
    }


def do_find_elements_fuzzy(
    query: str,
    control_type: Optional[str] = None,
    max_results: int = 20,
    min_score: float = 0.55,
    window_title: Optional[str] = None,
    window_handle: Optional[int] = None,
    app_id: str = "",
) -> dict[str, Any]:
    if sys.platform != "win32":
        return {"success": False, "error": "find_elements_fuzzy is Windows-only"}
    wt, hwnd, err = _resolve_scope(app_id, window_title)
    if err:
        return err
    hwnd = window_handle or hwnd

    from detection.fuzzy_match import fuzzy_match_elements
    from tools.ui_automation import do_list_elements

    listing = do_list_elements(
        window_title=wt or None,
        window_handle=hwnd,
        max_depth=8,
        include_offscreen=False,
        role=control_type or None,
    )
    matched = fuzzy_match_elements(
        listing.get("elements") or [],
        query,
        min_score=min_score,
        max_results=max_results,
    )
    return {
        "success": bool(matched),
        "count": len(matched),
        "elements": matched,
        "backend_used": listing.get("backend_used", ""),
    }


def do_get_tree_hash(
    window_title: Optional[str] = None,
    window_handle: Optional[int] = None,
    app_id: str = "",
    max_depth: int = 6,
) -> dict[str, Any]:
    if sys.platform != "win32":
        return {"success": False, "error": "get_tree_hash is Windows-only"}
    wt, hwnd, err = _resolve_scope(app_id, window_title)
    if err:
        return err
    hwnd = window_handle or hwnd

    from tools.ui_automation import do_list_elements

    listing = do_list_elements(
        window_title=wt or None,
        window_handle=hwnd,
        max_depth=max_depth,
        include_offscreen=False,
    )
    lines: list[str] = []
    for elem in listing.get("elements") or []:
        lines.append(
            f"{elem.get('role', '')}|{elem.get('automation_id', '')}|{elem.get('name', '')}"
        )
    lines.sort()
    digest = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()[:16]
    return {
        "success": True,
        "tree_hash": digest,
        "element_count": len(lines),
        "max_depth": max_depth,
    }


def do_get_element_bounds(
    automation_id: Optional[str] = None,
    name: Optional[str] = None,
    role: Optional[str] = None,
    index: int = 0,
    window_title: Optional[str] = None,
    window_handle: Optional[int] = None,
    app_id: str = "",
    fuzzy_match: bool = False,
) -> dict[str, Any]:
    if sys.platform != "win32":
        return {"success": False, "error": "get_element_bounds is Windows-only"}
    wt, hwnd, err = _resolve_scope(app_id, window_title)
    if err:
        return err
    hwnd = window_handle or hwnd

    elem: Optional[dict[str, Any]] = None
    if fuzzy_match and (name or automation_id):
        query = name or automation_id or ""
        fuzzy = do_find_elements_fuzzy(
            query,
            control_type=role,
            max_results=5,
            window_title=wt or None,
            window_handle=hwnd,
        )
        elems = fuzzy.get("elements") or []
        if elems:
            elem = elems[_resolve_index(index, len(elems))]
    else:
        from tools.ui_automation import do_find_element

        found = do_find_element(
            automation_id=automation_id,
            name=name,
            role=role,
            window_title=wt or None,
            window_handle=hwnd,
            index=index,
            remember=False,
        )
        if found.get("found") and found.get("elements"):
            elem = found["elements"][_resolve_index(index, len(found["elements"]))]

    if not elem:
        return {"success": False, "error": "Element not found"}

    return {
        "success": True,
        "bounds": {
            "x": int(elem.get("x") or 0),
            "y": int(elem.get("y") or 0),
            "width": int(elem.get("width") or 0),
            "height": int(elem.get("height") or 0),
        },
        "element": elem,
    }


def _find_element_for_action(
    automation_id: Optional[str],
    name: Optional[str],
    role: Optional[str],
    index: int,
    window_title: Optional[str],
    window_handle: Optional[int],
    fuzzy_match: bool = False,
) -> tuple[Optional[dict[str, Any]], Optional[dict[str, Any]]]:
    from tools.element_resolve import find_element_for_action

    return find_element_for_action(
        automation_id=automation_id,
        name=name,
        role=role,
        index=index,
        window_title=window_title,
        window_handle=window_handle,
        fuzzy_match=fuzzy_match,
    )


def do_double_click_element(
    automation_id: Optional[str] = None,
    name: Optional[str] = None,
    role: Optional[str] = None,
    index: int = 0,
    window_title: Optional[str] = None,
    window_handle: Optional[int] = None,
    app_id: str = "",
    fuzzy_match: bool = False,
) -> dict[str, Any]:
    wt, hwnd, err = _resolve_scope(app_id, window_title)
    if err:
        return err
    hwnd = window_handle or hwnd
    elem, find_err = _find_element_for_action(
        automation_id, name, role, index, wt or None, hwnd, fuzzy_match,
    )
    if find_err:
        return find_err
    from tools.input_tools import do_double_click
    from tools.ui_automation import _click_coords

    x, y = _click_coords(elem, wt or None)
    do_double_click(x, y)
    return {"success": True, "element": elem, "clicked_at": {"x": x, "y": y}, "method": "double_click"}


def do_right_click_element(
    automation_id: Optional[str] = None,
    name: Optional[str] = None,
    role: Optional[str] = None,
    index: int = 0,
    window_title: Optional[str] = None,
    window_handle: Optional[int] = None,
    app_id: str = "",
    fuzzy_match: bool = False,
) -> dict[str, Any]:
    wt, hwnd, err = _resolve_scope(app_id, window_title)
    if err:
        return err
    hwnd = window_handle or hwnd
    elem, find_err = _find_element_for_action(
        automation_id, name, role, index, wt or None, hwnd, fuzzy_match,
    )
    if find_err:
        return find_err
    from tools.input_tools import do_click
    from tools.ui_automation import _click_coords

    x, y = _click_coords(elem, wt or None)
    do_click(x, y, button="right")
    return {"success": True, "element": elem, "clicked_at": {"x": x, "y": y}, "method": "right_click"}


def do_drag_element(
    source_automation_id: Optional[str] = None,
    source_name: Optional[str] = None,
    source_control_type: Optional[str] = None,
    source_index: int = -1,
    target_automation_id: Optional[str] = None,
    target_name: Optional[str] = None,
    target_control_type: Optional[str] = None,
    target_index: int = -1,
    window_title: Optional[str] = None,
    window_handle: Optional[int] = None,
    app_id: str = "",
    duration: float = 0.5,
) -> dict[str, Any]:
    wt, hwnd, err = _resolve_scope(app_id, window_title)
    if err:
        return err
    hwnd = window_handle or hwnd
    src, src_err = _find_element_for_action(
        source_automation_id,
        source_name,
        source_control_type,
        source_index,
        wt or None,
        hwnd,
    )
    if src_err:
        return {**src_err, "phase": "source"}
    tgt, tgt_err = _find_element_for_action(
        target_automation_id,
        target_name,
        target_control_type,
        target_index,
        wt or None,
        hwnd,
    )
    if tgt_err:
        return {**tgt_err, "phase": "target"}

    from tools.input_tools import do_drag
    from tools.ui_automation import _click_coords

    sx, sy = _click_coords(src, wt or None)
    tx, ty = _click_coords(tgt, wt or None)
    drag = do_drag(sx, sy, tx, ty, duration=duration)
    return {
        "success": True,
        "source": src,
        "target": tgt,
        "from": {"x": sx, "y": sy},
        "to": {"x": tx, "y": ty},
        "drag": drag,
    }


def do_expand_collapse_element(
    action: str = "toggle",
    automation_id: Optional[str] = None,
    name: Optional[str] = None,
    window_title: Optional[str] = None,
    app_id: str = "",
) -> dict[str, Any]:
    wt, _hwnd, err = _resolve_scope(app_id, window_title)
    if err:
        return err
    from tools.ui_automation import do_expand_element

    act = (action or "toggle").lower()
    if act not in ("expand", "collapse", "toggle"):
        act = "toggle"
    return do_expand_element(
        name=name,
        automation_id=automation_id,
        window_title=wt or None,
        action=act,
    )


def do_select_option(
    option_text: str,
    automation_id: Optional[str] = None,
    name: Optional[str] = None,
    index: int = -1,
    window_title: Optional[str] = None,
    app_id: str = "",
) -> dict[str, Any]:
    wt, _hwnd, err = _resolve_scope(app_id, window_title)
    if err:
        return err
    from tools.control_items import do_select_control_item
    from tools.ui_automation import do_find_element

    found = do_find_element(
        automation_id=automation_id,
        name=name,
        role="ComboBox",
        window_title=wt or None,
        include_offscreen=True,
        remember=False,
    )
    if not found.get("found") or not found.get("elements"):
        found = do_find_element(
            automation_id=automation_id,
            name=name,
            window_title=wt or None,
            include_offscreen=True,
            remember=False,
        )
    elems = found.get("elements") or []
    if not elems:
        return {"success": False, "error": "ComboBox not found"}
    elem = elems[_resolve_index(index, len(elems))]
    aid = str(elem.get("automation_id") or "")
    if not aid:
        return {"success": False, "error": "ComboBox has no automation_id"}
    return do_select_control_item(aid, option_text, window_title=wt or None)


def do_type_into_element(
    text: str,
    automation_id: Optional[str] = None,
    name: Optional[str] = None,
    window_title: Optional[str] = None,
    app_id: str = "",
    clear_first: bool = True,
) -> dict[str, Any]:
    wt, _hwnd, err = _resolve_scope(app_id, window_title)
    if err:
        return err
    from tools.input_tools import do_send_keys, do_type_text
    from tools.ui_automation import do_click_element, do_set_element_value

    set_result = do_set_element_value(
        text if not clear_first else text,
        name=name,
        automation_id=automation_id,
        window_title=wt or None,
    )
    if set_result.get("success"):
        return {"success": True, "method": "ValuePattern", "text": text}

    click = do_click_element(
        name=name,
        automation_id=automation_id,
        window_title=wt or None,
        remember=False,
    )
    if not click.get("success"):
        return {"success": False, "error": click.get("error", "Element not found")}
    if clear_first:
        do_send_keys("ctrl+a")
    do_type_text(text)
    return {"success": True, "method": "click+type", "text": text}


def do_take_screenshot_optimized(
    max_tokens: int = 8000,
    window_title: Optional[str] = None,
    app_id: str = "",
) -> dict[str, Any]:
    wt, _hwnd, err = _resolve_scope(app_id, window_title)
    if err:
        return err
    from tools.screenshot import MAX_SCREENSHOT_WIDTH, capture_screenshot, get_dpi_scale

    shot = capture_screenshot(window_title=wt or None)
    from PIL import Image

    img = Image.open(io.BytesIO(base64.b64decode(shot["image"])))
    w, h = img.size
    # Rough token budget: ~0.75 tokens per 1k pixels at JPEG quality 85
    est_tokens = int((w * h) / 750)
    scale = 1.0
    if max_tokens > 0 and est_tokens > max_tokens:
        scale = (max_tokens / max(est_tokens, 1)) ** 0.5
        new_w = max(320, int(w * scale))
        new_h = max(240, int(h * scale))
        if new_w > MAX_SCREENSHOT_WIDTH:
            ratio = MAX_SCREENSHOT_WIDTH / new_w
            new_w = MAX_SCREENSHOT_WIDTH
            new_h = max(240, int(new_h * ratio))
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return {
            "success": True,
            "image": b64,
            "width": new_w,
            "height": new_h,
            "estimated_tokens": int((new_w * new_h) / 750),
            "scaled": True,
            "dpi_scale": get_dpi_scale(),
            "path": shot.get("path", ""),
        }
    return {
        "success": True,
        "image": shot["image"],
        "width": w,
        "height": h,
        "estimated_tokens": est_tokens,
        "scaled": False,
        "dpi_scale": get_dpi_scale(),
        "path": shot.get("path", ""),
    }


def do_annotate_screenshot(
    automation_ids: Optional[list[str]] = None,
    names: Optional[list[str]] = None,
    window_title: Optional[str] = None,
    app_id: str = "",
    output_path: Optional[str] = None,
) -> dict[str, Any]:
    wt, hwnd, err = _resolve_scope(app_id, window_title)
    if err:
        return err
    from PIL import Image, ImageDraw

    from tools.screenshot import capture_screenshot
    from tools.ui_automation import do_find_element

    shot = capture_screenshot(window_title=wt or None)
    img = Image.open(io.BytesIO(base64.b64decode(shot["image"])))
    draw = ImageDraw.Draw(img)
    boxes: list[dict[str, Any]] = []

    specs: list[tuple[Optional[str], Optional[str]]] = []
    for aid in automation_ids or []:
        specs.append((aid, None))
    for nm in names or []:
        specs.append((None, nm))

    for aid, nm in specs:
        found = do_find_element(
            automation_id=aid,
            name=nm,
            window_title=wt or None,
            window_handle=hwnd,
            remember=False,
        )
        if not found.get("elements"):
            continue
        elem = found["elements"][0]
        x = int(elem.get("x") or 0)
        y = int(elem.get("y") or 0)
        w = int(elem.get("width") or 0)
        h = int(elem.get("height") or 0)
        if w > 0 and h > 0:
            draw.rectangle([x, y, x + w, y + h], outline="red", width=3)
            boxes.append({"automation_id": aid, "name": nm, "x": x, "y": y, "width": w, "height": h})

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    saved_path = ""
    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(buf.getvalue())
        saved_path = str(out)
    return {
        "success": True,
        "image": b64,
        "boxes": boxes,
        "count": len(boxes),
        "output_path": saved_path,
    }


def do_compare_screenshot_files(
    image_path1: str,
    image_path2: str,
    output_path: Optional[str] = None,
    threshold: float = 0.02,
) -> dict[str, Any]:
    p1 = Path(image_path1)
    p2 = Path(image_path2)
    if not p1.is_file() or not p2.is_file():
        return {"success": False, "error": "One or both image paths do not exist"}

    from PIL import Image

    from tools.visual_diff import compute_visual_diff

    def _file_b64(path: Path) -> str:
        img = Image.open(path).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("ascii")

    b1 = _file_b64(p1)
    b2 = _file_b64(p2)
    diff = compute_visual_diff(b1, b2, threshold=threshold)
    out_path = output_path or str(p1.parent / f"diff_{p1.stem}_{p2.stem}.png")
    if diff.get("overlay_b64"):
        data = base64.b64decode(diff["overlay_b64"])
        Path(out_path).write_bytes(data)
    return {
        "success": True,
        "changed_fraction": diff.get("changed_fraction", 0.0),
        "is_identical": diff.get("is_identical", False),
        "bbox": diff.get("bbox"),
        "output_path": out_path,
    }


def do_click_element_hwnd(
    window_handle: int,
    automation_id: Optional[str] = None,
    name: Optional[str] = None,
    control_type: Optional[str] = None,
    fuzzy_match: bool = False,
    index: int = 0,
) -> dict[str, Any]:
    if fuzzy_match:
        return _click_hwnd_fuzzy(
            window_handle, automation_id, name, control_type, index,
        )
    from tools.ui_automation import do_click_element

    return do_click_element(
        automation_id=automation_id,
        name=name,
        role=control_type,
        window_handle=window_handle or None,
        index=index,
        remember=False,
    )


def _click_hwnd_fuzzy(
    window_handle: int,
    automation_id: Optional[str],
    name: Optional[str],
    control_type: Optional[str],
    index: int,
) -> dict[str, Any]:
    elem, err = _find_element_for_action(
        automation_id,
        name,
        control_type,
        index,
        None,
        window_handle,
        fuzzy_match=True,
    )
    if err:
        return err
    from tools.input_tools import do_click
    from tools.ui_automation import _click_coords

    x, y = _click_coords(elem, None)
    do_click(x, y)
    return {"success": True, "element": elem, "clicked_at": {"x": x, "y": y}, "method": "fuzzy_click"}


def do_set_value_hwnd(
    window_handle: int,
    value: str,
    automation_id: Optional[str] = None,
    name: Optional[str] = None,
    fuzzy_match: bool = False,
    index: int = 0,
) -> dict[str, Any]:
    if fuzzy_match:
        elem, err = _find_element_for_action(
            automation_id, name, None, index, None, window_handle, fuzzy_match=True,
        )
        if err:
            return err
        automation_id = elem.get("automation_id")
        name = elem.get("name")
    from tools.ui_automation import do_set_element_value

    return do_set_element_value(
        value,
        automation_id=automation_id,
        name=name,
        window_handle=window_handle or None,
        index=index,
    )


def do_get_snapshot_hwnd(
    window_handle: int,
    max_depth: int = 3,
    role: Optional[str] = None,
) -> dict[str, Any]:
    from tools.element_read_tools import do_get_snapshot

    return do_get_snapshot(
        window_handle=window_handle or None,
        max_depth=max_depth,
        role=role,
    )


def do_press_key(key: str) -> dict[str, Any]:
    from tools.input_tools import do_send_keys

    return do_send_keys((key or "").strip())


def do_press_key_combo(keys: list[str]) -> dict[str, Any]:
    from tools.input_tools import do_send_keys

    combo = "+".join(k.strip() for k in (keys or []) if k.strip())
    if not combo:
        return {"success": False, "error": "keys array is required"}
    return do_send_keys(combo)


def register(server) -> int:
    """Register WinApp parity tools."""
    import json

    from tools.params import resolve_window_title as _wt
    from tools.safety import ActionTimeoutError, with_timeout

    @server.tool()
    def attach_to_app(process_name: str) -> str:
        """Attach to a running process by name. Returns app_id for scoped tools."""
        try:
            result = with_timeout(lambda: do_attach_to_app(process_name), timeout=10.0)
        except ActionTimeoutError:
            return "Timed out attaching to app."
        return json.dumps(result, ensure_ascii=False)

    @server.tool()
    def attach_to_pid(pid: int) -> str:
        """Attach to a running process by PID. Returns app_id."""
        try:
            result = with_timeout(lambda: do_attach_to_pid(pid), timeout=10.0)
        except ActionTimeoutError:
            return "Timed out attaching to pid."
        return json.dumps(result, ensure_ascii=False)

    @server.tool()
    def list_apps() -> str:
        """List app_id sessions created by attach_to_app / attach_to_pid."""
        return json.dumps(do_list_apps(), ensure_ascii=False)

    @server.tool()
    def close_app(app_id: str) -> str:
        """Close application registered under app_id and remove session."""
        try:
            result = with_timeout(lambda: do_close_app(app_id), timeout=10.0)
        except ActionTimeoutError:
            return "Timed out closing app."
        return json.dumps(result, ensure_ascii=False)

    @server.tool()
    def list_desktop_windows() -> str:
        """List top-level windows with HWND, title, PID, and geometry."""
        try:
            result = with_timeout(do_list_desktop_windows, timeout=15.0)
        except ActionTimeoutError:
            return "Timed out listing desktop windows."
        lines = [f"count={result.get('count', 0)}"]
        for w in result.get("windows") or []:
            lines.append(
                f"hwnd={w.get('hwnd')} pid={w.get('pid')} "
                f"process={w.get('process')!r} title={w.get('title')!r}"
            )
        return "\n".join(lines)

    @server.tool()
    def release_keyboard() -> str:
        """Release stuck modifier keys (shift/ctrl/alt/win)."""
        return json.dumps(do_release_keyboard(), ensure_ascii=False)

    @server.tool()
    def find_elements(
        control_type: str = "",
        id_contains: str = "",
        name_contains: str = "",
        max_results: int = 50,
        window_title: str = "",
        title: str = "",
        window_handle: int = 0,
        app_id: str = "",
    ) -> str:
        """Search UIA elements with substring filters (WinApp parity)."""
        try:
            result = with_timeout(
                lambda: do_find_elements(
                    control_type=control_type or None,
                    id_contains=id_contains or None,
                    name_contains=name_contains or None,
                    max_results=max_results,
                    window_title=_wt(window_title, title),
                    window_handle=window_handle or None,
                    app_id=app_id,
                ),
                timeout=25.0,
            )
        except ActionTimeoutError:
            return "Timed out in find_elements."
        if not result.get("success"):
            return result.get("error", "find_elements: no matches")
        lines = [f"count={result.get('count', 0)}"]
        for i, elem in enumerate(result.get("elements") or []):
            lines.append(
                f"  [{i}] {elem.get('role', '')} id={elem.get('automation_id', '')!r} "
                f"name={elem.get('name', '')!r}"
            )
        return "\n".join(lines)

    @server.tool()
    def find_elements_fuzzy(
        query: str,
        control_type: str = "",
        max_results: int = 20,
        min_score: float = 0.55,
        window_title: str = "",
        title: str = "",
        window_handle: int = 0,
        app_id: str = "",
    ) -> str:
        """Fuzzy UIA search tolerating typos and partial names."""
        try:
            result = with_timeout(
                lambda: do_find_elements_fuzzy(
                    query,
                    control_type=control_type or None,
                    max_results=max_results,
                    min_score=min_score,
                    window_title=_wt(window_title, title),
                    window_handle=window_handle or None,
                    app_id=app_id,
                ),
                timeout=25.0,
            )
        except ActionTimeoutError:
            return "Timed out in find_elements_fuzzy."
        if not result.get("success"):
            return result.get("error", "find_elements_fuzzy: no matches")
        lines = [f"count={result.get('count', 0)}"]
        for i, elem in enumerate(result.get("elements") or []):
            lines.append(
                f"  [{i}] score={elem.get('fuzzy_score', 0)} "
                f"{elem.get('role', '')} id={elem.get('automation_id', '')!r} "
                f"name={elem.get('name', '')!r}"
            )
        return "\n".join(lines)

    @server.tool()
    def get_tree_hash(
        window_title: str = "",
        title: str = "",
        window_handle: int = 0,
        app_id: str = "",
        max_depth: int = 6,
    ) -> str:
        """Hash of visible UIA tree for change detection."""
        try:
            result = with_timeout(
                lambda: do_get_tree_hash(
                    window_title=_wt(window_title, title),
                    window_handle=window_handle or None,
                    app_id=app_id,
                    max_depth=max_depth,
                ),
                timeout=25.0,
            )
        except ActionTimeoutError:
            return "Timed out computing tree hash."
        if not result.get("success"):
            return result.get("error", "get_tree_hash failed")
        return (
            f"tree_hash={result.get('tree_hash')} "
            f"elements={result.get('element_count')} depth={result.get('max_depth')}"
        )

    @server.tool()
    def get_element_bounds(
        automation_id: str = "",
        name: str = "",
        role: str = "",
        index: int = 0,
        window_title: str = "",
        title: str = "",
        window_handle: int = 0,
        app_id: str = "",
        fuzzy_match: bool = False,
    ) -> str:
        """Return bounding box of a UIA element."""
        try:
            result = with_timeout(
                lambda: do_get_element_bounds(
                    automation_id=automation_id or None,
                    name=name or None,
                    role=role or None,
                    index=index,
                    window_title=_wt(window_title, title),
                    window_handle=window_handle or None,
                    app_id=app_id,
                    fuzzy_match=fuzzy_match,
                ),
                timeout=15.0,
            )
        except ActionTimeoutError:
            return "Timed out getting element bounds."
        if not result.get("success"):
            return result.get("error", "get_element_bounds failed")
        b = result.get("bounds") or {}
        return f"x={b.get('x')} y={b.get('y')} width={b.get('width')} height={b.get('height')}"

    @server.tool()
    def double_click_element(
        automation_id: str = "",
        name: str = "",
        role: str = "",
        index: int = 0,
        window_title: str = "",
        title: str = "",
        window_handle: int = 0,
        app_id: str = "",
        fuzzy_match: bool = False,
        capture: bool = False,
        capture_full: bool = False,
    ) -> str:
        """Double-click a UIA element by automation_id or name."""
        try:
            result = with_timeout(
                lambda: do_double_click_element(
                    automation_id=automation_id or None,
                    name=name or None,
                    role=role or None,
                    index=index,
                    window_title=_wt(window_title, title),
                    window_handle=window_handle or None,
                    app_id=app_id,
                    fuzzy_match=fuzzy_match,
                ),
                timeout=15.0,
            )
        except ActionTimeoutError:
            return "Timed out double-clicking element."
        if not result.get("success"):
            return result.get("error", "double_click_element failed")
        from tools.screenshot import action_tool_response

        msg = f"Double-clicked at ({result['clicked_at']['x']}, {result['clicked_at']['y']})."
        return action_tool_response(msg, capture=capture, capture_full=capture_full)

    @server.tool()
    def right_click_element(
        automation_id: str = "",
        name: str = "",
        role: str = "",
        index: int = 0,
        window_title: str = "",
        title: str = "",
        window_handle: int = 0,
        app_id: str = "",
        fuzzy_match: bool = False,
        capture: bool = False,
        capture_full: bool = False,
    ) -> str:
        """Right-click a UIA element by automation_id or name."""
        try:
            result = with_timeout(
                lambda: do_right_click_element(
                    automation_id=automation_id or None,
                    name=name or None,
                    role=role or None,
                    index=index,
                    window_title=_wt(window_title, title),
                    window_handle=window_handle or None,
                    app_id=app_id,
                    fuzzy_match=fuzzy_match,
                ),
                timeout=15.0,
            )
        except ActionTimeoutError:
            return "Timed out right-clicking element."
        if not result.get("success"):
            return result.get("error", "right_click_element failed")
        from tools.screenshot import action_tool_response

        msg = f"Right-clicked at ({result['clicked_at']['x']}, {result['clicked_at']['y']})."
        return action_tool_response(msg, capture=capture, capture_full=capture_full)

    @server.tool()
    def drag_element(
        source_automation_id: str = "",
        source_name: str = "",
        source_control_type: str = "",
        source_index: int = -1,
        target_automation_id: str = "",
        target_name: str = "",
        target_control_type: str = "",
        target_index: int = -1,
        window_title: str = "",
        title: str = "",
        window_handle: int = 0,
        app_id: str = "",
        duration: float = 0.5,
        capture: bool = False,
        capture_full: bool = False,
    ) -> str:
        """Drag from source element to target element (center to center)."""
        try:
            result = with_timeout(
                lambda: do_drag_element(
                    source_automation_id=source_automation_id or None,
                    source_name=source_name or None,
                    source_control_type=source_control_type or None,
                    source_index=source_index,
                    target_automation_id=target_automation_id or None,
                    target_name=target_name or None,
                    target_control_type=target_control_type or None,
                    target_index=target_index,
                    window_title=_wt(window_title, title),
                    window_handle=window_handle or None,
                    app_id=app_id,
                    duration=duration,
                ),
                timeout=20.0,
            )
        except ActionTimeoutError:
            return "Timed out dragging element."
        if not result.get("success"):
            return result.get("error", "drag_element failed")
        from tools.screenshot import action_tool_response

        msg = (
            f"Dragged ({result['from']['x']}, {result['from']['y']}) -> "
            f"({result['to']['x']}, {result['to']['y']})."
        )
        return action_tool_response(msg, capture=capture, capture_full=capture_full)

    @server.tool()
    def expand_collapse_element(
        action: str = "toggle",
        automation_id: str = "",
        name: str = "",
        window_title: str = "",
        title: str = "",
        app_id: str = "",
    ) -> str:
        """Expand, collapse, or toggle an ExpandCollapse control."""
        try:
            result = with_timeout(
                lambda: do_expand_collapse_element(
                    action=action,
                    automation_id=automation_id or None,
                    name=name or None,
                    window_title=_wt(window_title, title),
                    app_id=app_id,
                ),
                timeout=15.0,
            )
        except ActionTimeoutError:
            return "Timed out expand/collapse."
        if result.get("success"):
            return f"expand_collapse_element: {action} OK"
        return result.get("error", "expand_collapse_element failed")

    @server.tool()
    def select_option(
        option_text: str,
        automation_id: str = "",
        name: str = "",
        index: int = -1,
        window_title: str = "",
        title: str = "",
        app_id: str = "",
    ) -> str:
        """Select ComboBox option by visible text (one-shot)."""
        try:
            result = with_timeout(
                lambda: do_select_option(
                    option_text,
                    automation_id=automation_id or None,
                    name=name or None,
                    index=index,
                    window_title=_wt(window_title, title),
                    app_id=app_id,
                ),
                timeout=20.0,
            )
        except ActionTimeoutError:
            return "Timed out selecting option."
        if result.get("success"):
            return f"select_option: selected '{option_text}'"
        return result.get("error", "select_option failed")

    @server.tool()
    def type_into_element(
        text: str,
        automation_id: str = "",
        name: str = "",
        window_title: str = "",
        title: str = "",
        app_id: str = "",
        clear_first: bool = True,
    ) -> str:
        """Type text into a field found by automation_id or name (WinApp type_text parity)."""
        try:
            result = with_timeout(
                lambda: do_type_into_element(
                    text,
                    automation_id=automation_id or None,
                    name=name or None,
                    window_title=_wt(window_title, title),
                    app_id=app_id,
                    clear_first=clear_first,
                ),
                timeout=15.0,
            )
        except ActionTimeoutError:
            return "Timed out typing into element."
        if result.get("success"):
            return f"type_into_element: typed {len(text)} chars via {result.get('method')}"
        return result.get("error", "type_into_element failed")

    @server.tool()
    def take_screenshot_optimized(
        max_tokens: int = 8000,
        window_title: str = "",
        title: str = "",
        app_id: str = "",
    ) -> str:
        """Screenshot resized to fit an approximate LLM token budget."""
        try:
            result = with_timeout(
                lambda: do_take_screenshot_optimized(
                    max_tokens=max_tokens,
                    window_title=_wt(window_title, title),
                    app_id=app_id,
                ),
                timeout=15.0,
            )
        except ActionTimeoutError:
            return "Timed out taking optimized screenshot."
        if not result.get("success"):
            return result.get("error", "take_screenshot_optimized failed")
        return (
            f"optimized screenshot {result.get('width')}x{result.get('height')} "
            f"tokens~{result.get('estimated_tokens')} scaled={result.get('scaled')} "
            f"path={result.get('path', '')}"
        )

    @server.tool()
    def annotate_screenshot(
        automation_ids: list[str] = [],
        names: list[str] = [],
        window_title: str = "",
        title: str = "",
        app_id: str = "",
        output_path: str = "",
    ) -> str:
        """Screenshot with red boxes around specified elements."""
        try:
            result = with_timeout(
                lambda: do_annotate_screenshot(
                    automation_ids=automation_ids or None,
                    names=names or None,
                    window_title=_wt(window_title, title),
                    app_id=app_id,
                    output_path=output_path or None,
                ),
                timeout=20.0,
            )
        except ActionTimeoutError:
            return "Timed out annotating screenshot."
        if not result.get("success"):
            return result.get("error", "annotate_screenshot failed")
        path_note = f" path={result.get('output_path')}" if result.get("output_path") else ""
        return f"annotate_screenshot: {result.get('count', 0)} boxes drawn{path_note}"

    @server.tool()
    def compare_screenshot_files(
        image_path1: str,
        image_path2: str,
        output_path: str = "",
        threshold: float = 0.02,
    ) -> str:
        """Pixel diff between two screenshot files (WinApp screenshot_diff parity)."""
        try:
            result = with_timeout(
                lambda: do_compare_screenshot_files(
                    image_path1,
                    image_path2,
                    output_path=output_path or None,
                    threshold=threshold,
                ),
                timeout=20.0,
            )
        except ActionTimeoutError:
            return "Timed out comparing screenshots."
        if not result.get("success"):
            return result.get("error", "compare_screenshot_files failed")
        return (
            f"changed_fraction={result.get('changed_fraction')} "
            f"identical={result.get('is_identical')} output={result.get('output_path')}"
        )

    @server.tool()
    def click_element_hwnd(
        window_handle: int,
        automation_id: str = "",
        name: str = "",
        control_type: str = "",
        fuzzy_match: bool = False,
        index: int = 0,
        capture: bool = False,
        capture_full: bool = False,
    ) -> str:
        """Click element scoped to a specific HWND."""
        try:
            result = with_timeout(
                lambda: do_click_element_hwnd(
                    window_handle,
                    automation_id=automation_id or None,
                    name=name or None,
                    control_type=control_type or None,
                    fuzzy_match=fuzzy_match,
                    index=index,
                ),
                timeout=15.0,
            )
        except ActionTimeoutError:
            return "Timed out click_element_hwnd."
        if not result.get("success"):
            return result.get("error", "click_element_hwnd failed")
        from tools.screenshot import action_tool_response

        pt = result.get("clicked_at") or {}
        msg = f"Clicked hwnd={window_handle} at ({pt.get('x')}, {pt.get('y')})."
        return action_tool_response(msg, capture=capture, capture_full=capture_full)

    @server.tool()
    def set_value_hwnd(
        window_handle: int,
        value: str,
        automation_id: str = "",
        name: str = "",
        fuzzy_match: bool = False,
        index: int = 0,
    ) -> str:
        """Set value on element scoped to HWND."""
        try:
            result = with_timeout(
                lambda: do_set_value_hwnd(
                    window_handle,
                    value,
                    automation_id=automation_id or None,
                    name=name or None,
                    fuzzy_match=fuzzy_match,
                    index=index,
                ),
                timeout=15.0,
            )
        except ActionTimeoutError:
            return "Timed out set_value_hwnd."
        if result.get("success"):
            return f"set_value_hwnd: value set on hwnd={window_handle}"
        return result.get("error", "set_value_hwnd failed")

    @server.tool()
    def get_snapshot_hwnd(
        window_handle: int,
        max_depth: int = 3,
        role: str = "",
    ) -> str:
        """Compact UIA snapshot scoped to HWND."""
        try:
            result = with_timeout(
                lambda: do_get_snapshot_hwnd(
                    window_handle,
                    max_depth=max_depth,
                    role=role or None,
                ),
                timeout=25.0,
            )
        except ActionTimeoutError:
            return "Timed out get_snapshot_hwnd."
        if not result.get("success"):
            return result.get("error", "get_snapshot_hwnd failed")
        lines = [f"count={result.get('count', 0)} hwnd={window_handle}"]
        for node in (result.get("nodes") or [])[:40]:
            lines.append(
                f"  {node.get('role', '')} id={node.get('automation_id', '')!r} "
                f"name={node.get('name', '')!r}"
            )
        return "\n".join(lines)

    @server.tool()
    def press_key(key: str) -> str:
        """Press a single key (RETURN, TAB, ESCAPE, F5, etc.)."""
        try:
            with_timeout(lambda: do_press_key(key), timeout=5.0)
        except ActionTimeoutError:
            return "Timed out press_key."
        return f"press_key: {key}"

    @server.tool()
    def press_key_combo(keys: list[str]) -> str:
        """Press a keyboard shortcut (e.g. ['ctrl','s'])."""
        try:
            with_timeout(lambda: do_press_key_combo(keys), timeout=5.0)
        except ActionTimeoutError:
            return "Timed out press_key_combo."
        return f"press_key_combo: {'+'.join(keys)}"

    return 24

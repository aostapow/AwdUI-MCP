"""Element read helpers — find_all, read_element, read by index."""
from __future__ import annotations

import json
import sys
from typing import Any, Optional


def do_find_all_elements(
    automation_id: Optional[str] = None,
    name: Optional[str] = None,
    role: Optional[str] = None,
    window_title: Optional[str] = None,
    window_handle: Optional[int] = None,
    include_offscreen: bool = False,
) -> dict[str, Any]:
    if sys.platform != "win32":
        return {"success": False, "error": "find_all_elements is Windows-only"}
    from tools.ui_automation import do_find_element

    result = do_find_element(
        automation_id=automation_id,
        name=name,
        role=role,
        window_title=window_title,
        include_offscreen=include_offscreen,
        index=0,
        window_handle=window_handle,
        remember=False,
    )
    elements = []
    for idx, elem in enumerate(result.get("elements") or []):
        row = dict(elem)
        row["index"] = idx
        elements.append(row)
    return {
        "success": bool(elements),
        "found": bool(elements),
        "count": len(elements),
        "elements": elements,
        "backend_used": result.get("backend_used", ""),
    }


def do_read_element(
    automation_id: Optional[str] = None,
    name: Optional[str] = None,
    role: Optional[str] = None,
    window_title: Optional[str] = None,
    window_handle: Optional[int] = None,
    index: int = 0,
) -> dict[str, Any]:
    if sys.platform != "win32":
        return {"success": False, "error": "read_element is Windows-only"}
    from tools.ui_automation import do_get_element_properties

    props = do_get_element_properties(
        name=name,
        automation_id=automation_id,
        window_title=window_title,
        window_handle=window_handle,
    )
    if props.get("found"):
        return {
            "success": True,
            "index": index,
            "properties": props.get("properties") or {},
            "backend_used": props.get("backend_used", ""),
        }

    all_hits = do_find_all_elements(
        automation_id=automation_id,
        name=name,
        role=role,
        window_title=window_title,
        window_handle=window_handle,
        include_offscreen=True,
    )
    if not all_hits.get("elements"):
        return {"success": False, "error": "Element not found"}
    idx = min(max(0, int(index or 0)), len(all_hits["elements"]) - 1)
    elem = all_hits["elements"][idx]
    return {
        "success": True,
        "index": idx,
        "properties": elem,
        "backend_used": all_hits.get("backend_used", ""),
    }


def do_read_element_by_index(
    index: int,
    automation_id: Optional[str] = None,
    name: Optional[str] = None,
    role: Optional[str] = None,
    window_title: Optional[str] = None,
    window_handle: Optional[int] = None,
) -> dict[str, Any]:
    return do_read_element(
        automation_id=automation_id,
        name=name,
        role=role,
        window_title=window_title,
        window_handle=window_handle,
        index=index,
    )


def do_get_snapshot(
    window_title: Optional[str] = None,
    window_handle: Optional[int] = None,
    max_depth: int = 3,
    role: Optional[str] = None,
) -> dict[str, Any]:
    if sys.platform != "win32":
        return {"success": False, "error": "get_snapshot is Windows-only"}
    from tools.ui_automation import do_list_elements

    listing = do_list_elements(
        window_title=window_title,
        window_handle=window_handle,
        max_depth=max_depth,
        role=role,
        include_offscreen=False,
    )
    nodes = []
    for elem in listing.get("elements") or []:
        nodes.append(
            {
                "role": elem.get("role", ""),
                "name": elem.get("name", ""),
                "automation_id": elem.get("automation_id", ""),
                "x": elem.get("x", 0),
                "y": elem.get("y", 0),
                "width": elem.get("width", 0),
                "height": elem.get("height", 0),
            }
        )
    return {
        "success": True,
        "count": len(nodes),
        "max_depth": max_depth,
        "window_handle": int(window_handle or 0),
        "nodes": nodes,
        "backend_used": listing.get("backend_used", ""),
    }


def register(server) -> int:
    from tools.params import resolve_window_title as _wt
    from tools.safety import ActionTimeoutError, with_timeout

    @server.tool()
    def find_all_elements(
        automation_id: str = "",
        name: str = "",
        role: str = "",
        window_title: str = "",
        title: str = "",
        window_handle: int = 0,
    ) -> str:
        """List all matching elements with index (for disambiguating duplicates)."""
        try:
            result = with_timeout(
                lambda: do_find_all_elements(
                    automation_id=automation_id or None,
                    name=name or None,
                    role=role or None,
                    window_title=_wt(window_title, title),
                    window_handle=window_handle or None,
                ),
                timeout=20.0,
            )
        except ActionTimeoutError:
            return "Timed out finding elements."
        if not result.get("success"):
            return result.get("error", "find_all_elements: no matches")
        lines = [f"count={result.get('count', 0)} backend={result.get('backend_used', '')}"]
        for elem in result.get("elements") or []:
            lines.append(
                f"  [{elem.get('index')}] {elem.get('role', '')} "
                f"id={elem.get('automation_id', '')!r} name={elem.get('name', '')!r}"
            )
        return "\n".join(lines)

    @server.tool()
    def read_element(
        automation_id: str = "",
        name: str = "",
        role: str = "",
        window_title: str = "",
        title: str = "",
        window_handle: int = 0,
        index: int = 0,
    ) -> str:
        """Read properties of a UI element (by automation_id/name; optional index)."""
        try:
            result = with_timeout(
                lambda: do_read_element(
                    automation_id=automation_id or None,
                    name=name or None,
                    role=role or None,
                    window_title=_wt(window_title, title),
                    window_handle=window_handle or None,
                    index=index,
                ),
                timeout=15.0,
            )
        except ActionTimeoutError:
            return "Timed out reading element."
        if not result.get("success"):
            return result.get("error", "read_element failed")
        return json.dumps(
            {
                "index": result.get("index", 0),
                "properties": result.get("properties") or {},
            },
            ensure_ascii=False,
        )

    @server.tool()
    def read_element_by_index(
        index: int,
        automation_id: str = "",
        name: str = "",
        role: str = "",
        window_title: str = "",
        title: str = "",
        window_handle: int = 0,
    ) -> str:
        """Read element properties by index from find_all_elements results."""
        try:
            result = with_timeout(
                lambda: do_read_element_by_index(
                    index=index,
                    automation_id=automation_id or None,
                    name=name or None,
                    role=role or None,
                    window_title=_wt(window_title, title),
                    window_handle=window_handle or None,
                ),
                timeout=15.0,
            )
        except ActionTimeoutError:
            return "Timed out reading element by index."
        if not result.get("success"):
            return result.get("error", "read_element_by_index failed")
        return json.dumps(
            {
                "index": result.get("index", index),
                "properties": result.get("properties") or {},
            },
            ensure_ascii=False,
        )

    @server.tool()
    def get_snapshot(
        window_title: str = "",
        title: str = "",
        window_handle: int = 0,
        max_depth: int = 3,
        role: str = "",
    ) -> str:
        """Compact UI tree snapshot (like browser DOM) for a window or HWND modal."""
        try:
            result = with_timeout(
                lambda: do_get_snapshot(
                    window_title=_wt(window_title, title),
                    window_handle=window_handle or None,
                    max_depth=max_depth,
                    role=role or None,
                ),
                timeout=30.0,
            )
        except ActionTimeoutError:
            return "Timed out building snapshot."
        if not result.get("success"):
            return result.get("error", "get_snapshot failed")
        return json.dumps(result, ensure_ascii=False)

    return 4

"""Batch form fill and read helpers."""
from __future__ import annotations

import json
import sys
from typing import Any, Optional


def _parse_fields(fields: Any) -> list[dict[str, Any]]:
    if fields is None:
        return []
    if isinstance(fields, str):
        raw = fields.strip()
        if not raw:
            return []
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return [
                {"automation_id": k, "value": v}
                for k, v in parsed.items()
            ]
        if isinstance(parsed, list):
            return parsed
        return []
    if isinstance(fields, list):
        return fields
    return []


def do_fill_form(
    fields: Any,
    window_title: Optional[str] = None,
    window_handle: Optional[int] = None,
) -> dict[str, Any]:
    if sys.platform != "win32":
        return {"success": False, "error": "fill_form is Windows-only"}

    items = _parse_fields(fields)
    if not items:
        return {"success": False, "error": "no fields provided", "filled": 0}

    from tools.ui_automation import do_set_element_value

    filled = 0
    errors: list[dict[str, Any]] = []
    for item in items:
        value = item.get("value", "")
        result = do_set_element_value(
            value=str(value),
            automation_id=(item.get("automation_id") or None),
            name=(item.get("name") or None),
            window_title=window_title,
            window_handle=window_handle,
            index=int(item.get("index", 0) or 0),
        )
        if result.get("success"):
            filled += 1
        else:
            errors.append(
                {
                    "automation_id": item.get("automation_id", ""),
                    "name": item.get("name", ""),
                    "error": result.get("error", "set failed"),
                }
            )

    return {
        "success": filled == len(items),
        "filled": filled,
        "total": len(items),
        "errors": errors,
    }


def do_get_all_values(
    window_title: Optional[str] = None,
    window_handle: Optional[int] = None,
    max_depth: int = 12,
) -> dict[str, Any]:
    if sys.platform != "win32":
        return {"success": False, "error": "get_all_values is Windows-only"}
    from detection.form_read import get_all_values

    payload = get_all_values(
        window_title=window_title,
        window_handle=window_handle,
        max_depth=max_depth,
    )
    return {"success": True, **payload}


def register(server) -> int:
    from tools.params import resolve_window_title as _wt
    from tools.safety import ActionTimeoutError, with_timeout

    @server.tool()
    def fill_form(
        fields_json: str = "",
        fields: str = "",
        window_title: str = "",
        title: str = "",
        window_handle: int = 0,
    ) -> str:
        """Fill multiple form fields in one call (AutomationId or Name per field).

        Pass ``fields_json`` as a JSON array [{automation_id,name,value,index}] or
        object {FieldId: value}. Much faster than repeated set_element_value.
        """
        payload = fields_json or fields
        if not payload:
            return "fields_json is required"
        try:
            result = with_timeout(
                lambda: do_fill_form(
                    fields=payload,
                    window_title=_wt(window_title, title),
                    window_handle=window_handle or None,
                ),
                timeout=60.0,
            )
        except ActionTimeoutError:
            return "Timed out filling form."
        if not result.get("success"):
            err = result.get("errors") or []
            return f"FAIL filled={result.get('filled', 0)}/{result.get('total', 0)} errors={err}"
        return f"OK filled={result.get('filled', 0)}/{result.get('total', 0)}"

    @server.tool()
    def get_all_values(
        window_title: str = "",
        title: str = "",
        window_handle: int = 0,
        max_depth: int = 12,
    ) -> str:
        """Read all editable fields (Edit, ComboBox, CheckBox, etc.) in the window."""
        import json

        try:
            result = with_timeout(
                lambda: do_get_all_values(
                    window_title=_wt(window_title, title),
                    window_handle=window_handle or None,
                    max_depth=max_depth,
                ),
                timeout=30.0,
            )
        except ActionTimeoutError:
            return "Timed out reading form values."
        if not result.get("success"):
            return result.get("error", "get_all_values failed")
        return json.dumps(
            {
                "count": result.get("count", 0),
                "values": result.get("values") or {},
                "backend_used": result.get("backend_used", ""),
            },
            ensure_ascii=False,
        )

    return 2

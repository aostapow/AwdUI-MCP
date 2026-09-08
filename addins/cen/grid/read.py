"""Orchestrate COBIS grid reading strategies."""
from __future__ import annotations

from typing import Any, Optional

from grid.detect import detect_grid_type
from grid.farpoint_cells import collect_farpoint_cells
from grid.msaa_cells import collect_msaa_values
from grid.resolve import resolve_grid
from grid.spatial_cells import collect_spatial_grid


def _sample_child_names(raw, limit: int = 40) -> list[str]:
    from detection.uia_tree import _walk_control_tree, _wrap_raw

    names: list[str] = []
    for child in _walk_control_tree(raw):
        if len(names) >= limit:
            break
        det = _wrap_raw(child)
        if det and (det.name or getattr(det, "accessible_description", "")):
            names.append(f"{det.name} {getattr(det, 'accessible_description', '')}")
    return names


def _page_payload(payload: dict[str, Any], offset: int, limit: int) -> dict[str, Any]:
    rows = payload.get("rows") or []
    start = max(0, int(offset or 0))
    end = start + max(1, min(int(limit or 200), 500))
    page = rows[start:end]
    out = dict(payload)
    out["rows"] = page
    out["row_count"] = len(page)
    out["offset"] = start
    out["limit"] = int(limit or 200)
    out["has_more"] = end < len(rows)
    out["total_rows"] = len(rows)
    return out


def _try_core_read_table(raw, offset: int, limit: int) -> Optional[dict[str, Any]]:
    from detection.table_read import read_table

    hit = read_table(raw, offset=offset, limit=limit)
    if hit and hit.get("rows"):
        hit = dict(hit)
        hit["source"] = f"cen_{hit.get('source', 'core')}"
        return hit
    return None


def detect_cobis_grid(
    automation_id: str = "",
    name: str = "",
    window_title: Optional[str] = None,
) -> dict[str, Any]:
    raw, element, scope = resolve_grid(automation_id, name, window_title)
    if not raw:
        return {"success": False, **scope}

    sample = _sample_child_names(raw)
    detected = detect_grid_type(element, sample)
    return {
        "success": True,
        "automation_id": element.get("automation_id") or automation_id or name,
        "name": element.get("name") or name,
        "class_name": element.get("class_name", ""),
        "role": element.get("role", ""),
        "resolved_window_title": scope.get("resolved_title") or window_title or "",
        "sample_children": sample[:8],
        **detected,
    }


def read_cobis_grid(
    automation_id: str = "",
    name: str = "",
    window_title: Optional[str] = None,
    offset: int = 0,
    limit: int = 200,
) -> dict[str, Any]:
    raw, element, scope = resolve_grid(automation_id, name, window_title)
    if not raw:
        return {"success": False, **scope}

    detected = detect_grid_type(element, _sample_child_names(raw))
    grid_type = detected.get("grid_type", "unknown")
    index_base = int(detected.get("index_base") or 1)
    strategies_tried: list[str] = []

    payload: Optional[dict[str, Any]] = None
    if grid_type == "uia_table" or detected.get("reader") == "core_read_table":
        payload = _try_core_read_table(raw, offset, limit)
        if payload:
            strategies_tried.append("core_read_table")

    if not payload:
        payload = collect_farpoint_cells(raw, index_base=index_base)
        if payload:
            strategies_tried.append("farpoint_uia")
            payload = _page_payload(payload, offset, limit)

    if not payload:
        payload = collect_spatial_grid(raw, element)
        if payload:
            strategies_tried.append("spatial_uia")
            payload = _page_payload(payload, offset, limit)

    if not payload:
        payload = collect_msaa_values(raw)
        if payload:
            strategies_tried.append("msaa")
            payload = _page_payload(payload, offset, limit)

    if not payload:
        payload = _try_core_read_table(raw, offset, limit)
        if payload:
            strategies_tried.append("core_read_table_fallback")

    if not payload or not payload.get("rows"):
        return {
            "success": False,
            "error": "No grid data readable via UIA/MSAA",
            "grid_type": grid_type,
            "strategies_tried": strategies_tried,
            "automation_id": element.get("automation_id") or automation_id or name,
            "resolved_window_title": scope.get("resolved_title") or "",
        }

    return {
        "success": True,
        "automation_id": element.get("automation_id") or automation_id or name,
        "resolved_window_title": scope.get("resolved_title") or window_title or "",
        "grid_type": grid_type,
        "strategies_tried": strategies_tried,
        **payload,
    }


def read_cobis_grid_cell(
    automation_id: str = "",
    name: str = "",
    row: int = 1,
    column: int = 1,
    window_title: Optional[str] = None,
) -> dict[str, Any]:
    if row < 0 or column < 0:
        return {"success": False, "error": "row and column must be >= 0"}

    table = read_cobis_grid(
        automation_id=automation_id,
        name=name,
        window_title=window_title,
        offset=0,
        limit=500,
    )
    if not table.get("success"):
        return table

    headers = table.get("headers") or []
    rows = table.get("rows") or []
    index_base = int(table.get("index_base") or 1)
    data_row = int(row) - index_base if index_base == 1 else int(row)
    data_col = int(column) - index_base if index_base == 1 else int(column)

    if data_row < 0 or data_row >= len(rows):
        return {
            "success": False,
            "error": f"row {row} out of range (data rows={len(rows)})",
            "index_base": index_base,
        }
    row_vals = rows[data_row]
    if data_col < 0 or data_col >= len(row_vals):
        return {
            "success": False,
            "error": f"column {column} out of range (cols={len(row_vals)})",
            "index_base": index_base,
        }

    header = headers[data_col] if data_col < len(headers) else f"col_{column}"
    return {
        "success": True,
        "row": row,
        "column": column,
        "column_name": header,
        "value": row_vals[data_col],
        "index_base": index_base,
        "grid_type": table.get("grid_type"),
        "source": table.get("source"),
    }

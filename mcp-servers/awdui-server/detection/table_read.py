"""Read full grid/table as headers + rows (UIA Grid/Table + DevExpress fallback)."""
from __future__ import annotations

from typing import Any, Optional

from detection.grid_rows import group_grid_rows, row_matches
from detection.uia_text import get_cell_text
from detection.uia_tree import _walk_control_tree, _wrap_raw


def _clamp_limit(limit: int) -> int:
    return max(1, min(int(limit or 200), 500))


def _headers_from_cells(rows: list[dict[str, Any]]) -> list[str]:
    cols: set[str] = set()
    for row in rows:
        cols.update((row.get("cells") or {}).keys())
    return sorted(cols)


def _collect_header_items(root) -> list[str]:
    headers: list[str] = []
    for raw in _walk_control_tree(root):
        det = _wrap_raw(raw)
        if not det or (det.role or "") != "HeaderItem":
            continue
        text = (get_cell_text(raw) or det.name or "").strip()
        if text:
            headers.append(text)
    return headers


def _cell_value_from_raw(cell_raw) -> str:
    if cell_raw is None:
        return ""
    try:
        from pywinauto.controls.uiawrapper import UIAWrapper

        wrapper = cell_raw if hasattr(cell_raw, "element_info") else UIAWrapper(cell_raw)
    except Exception:
        wrapper = cell_raw
    text = (get_cell_text(wrapper) or "").strip()
    if text:
        return text
    try:
        from detection.backends.uia_backend import _pywinauto_to_element

        det = _pywinauto_to_element(wrapper)
        if det:
            return (det.name or getattr(det, "value", "") or "").strip()
    except Exception:
        pass
    return ""


def _wrap_grid_cell(cell_raw):
    if cell_raw is None:
        return None
    if hasattr(cell_raw, "element_info"):
        return cell_raw
    try:
        from pywinauto.controls.uiawrapper import UIAWrapper

        return UIAWrapper(cell_raw)
    except Exception:
        return cell_raw


def read_table_pattern(
    raw,
    offset: int = 0,
    limit: int = 200,
) -> Optional[dict[str, Any]]:
    """Read table via UIA GridPattern or TablePattern."""
    try:
        from pywinauto.uia_defines import get_elem_interface

        element = raw.element_info.element
    except Exception:
        return None

    page_limit = _clamp_limit(limit)
    start = max(0, int(offset or 0))

    for pattern_name in ("Grid", "Table"):
        try:
            pattern = get_elem_interface(element, pattern_name)
            row_count = int(pattern.CurrentRowCount)
            col_count = int(pattern.CurrentColumnCount)
        except Exception:
            continue
        if row_count <= 0 or col_count <= 0:
            continue

        headers = _collect_header_items(raw)
        if len(headers) != col_count:
            headers = [f"column_{idx}" for idx in range(col_count)]

        end = min(row_count, start + page_limit)
        rows: list[list[str]] = []
        for row_idx in range(start, end):
            row_vals: list[str] = []
            for col_idx in range(col_count):
                try:
                    cell_raw = pattern.GetItem(row_idx, col_idx)
                    row_vals.append(_cell_value_from_raw(_wrap_grid_cell(cell_raw)))
                except Exception:
                    row_vals.append("")
            rows.append(row_vals)

        return {
            "headers": headers,
            "rows": rows,
            "row_count": len(rows),
            "total_rows": row_count,
            "offset": start,
            "limit": page_limit,
            "has_more": end < row_count,
            "source": f"uia_{pattern_name.lower()}",
        }
    return None


def read_table_devexpress(
    raw,
    filter_text: str = "",
    offset: int = 0,
    limit: int = 200,
) -> Optional[dict[str, Any]]:
    """Assemble DevExpress-style grid from DataItem cells."""
    page_limit = _clamp_limit(limit)
    start = max(0, int(offset or 0))
    grouped = group_grid_rows(raw)
    if not grouped:
        return None

    filtered = [row for row in grouped if row_matches(row, filter_text)]
    headers = _headers_from_cells(filtered)
    if not headers:
        return None

    page = filtered[start : start + page_limit]
    rows: list[list[str]] = []
    for row in page:
        cells = row.get("cells") or {}
        rows.append([str(cells.get(header, "") or "") for header in headers])

    return {
        "headers": headers,
        "rows": rows,
        "row_count": len(rows),
        "total_rows": len(filtered),
        "offset": start,
        "limit": page_limit,
        "has_more": start + len(page) < len(filtered),
        "source": "grid_rows",
    }


def read_table(
    raw,
    filter_text: str = "",
    offset: int = 0,
    limit: int = 200,
) -> Optional[dict[str, Any]]:
    """Return table payload `{headers, rows, ...}` using best available strategy."""
    pattern_hit = read_table_pattern(raw, offset=offset, limit=limit)
    if pattern_hit and pattern_hit.get("rows"):
        return pattern_hit

    devexpress_hit = read_table_devexpress(
        raw,
        filter_text=filter_text,
        offset=offset,
        limit=limit,
    )
    if devexpress_hit:
        return devexpress_hit

    if pattern_hit:
        return pattern_hit
    return devexpress_hit


def public_table_payload(payload: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if not payload:
        return None
    return {
        key: payload[key]
        for key in (
            "headers",
            "rows",
            "row_count",
            "total_rows",
            "offset",
            "limit",
            "has_more",
            "source",
        )
        if key in payload
    }

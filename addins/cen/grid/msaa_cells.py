"""MSAA fallback reader for legacy grid HWNDs."""
from __future__ import annotations

from typing import Any, Optional


def _grid_hwnd(raw) -> int:
    try:
        return int(raw.element_info.handle or 0)
    except Exception:
        return 0


def collect_msaa_values(raw, max_items: int = 500) -> dict[str, Any]:
    """Collect accValue/accName leaves under grid HWND."""
    hwnd = _grid_hwnd(raw)
    if hwnd <= 0:
        return {}

    try:
        from detection.backends.msaa_backend import (
            CHILDID_SELF,
            _acc_to_element,
            _get_oleacc,
            _walk_accessible,
        )
    except Exception:
        return {}

    try:
        _, accessible_from_window = _get_oleacc()
        acc = accessible_from_window(hwnd)
    except Exception:
        return {}

    collected: list[tuple[int, int, str]] = []
    raw_walk: list = []
    _walk_accessible(acc, CHILDID_SELF, 0, 12, raw_walk)
    for _acc, child_id, elem in raw_walk:
        text = (elem.value or elem.name or "").strip()
        if not text:
            continue
        collected.append((int(elem.y), int(elem.x), text))
        if len(collected) >= max_items:
            break

    if not collected:
        return {}

    collected.sort(key=lambda t: (t[0], t[1]))
    bands: list[list[tuple[int, int, str]]] = []
    y_tol = 10
    for item in collected:
        if not bands or abs(item[0] - bands[-1][0][0]) > y_tol:
            bands.append([item])
        else:
            bands[-1].append(item)

    rows: list[list[str]] = []
    for band in bands:
        band.sort(key=lambda t: t[1])
        rows.append([t[2] for t in band])

    if len(rows) >= 2:
        headers, data = rows[0], rows[1:]
    else:
        headers = [f"col_{i}" for i in range(len(rows[0]) if rows else 0)]
        data = rows

    return {
        "headers": headers,
        "rows": data,
        "row_count": len(data),
        "total_rows": len(data),
        "offset": 0,
        "limit": len(data),
        "has_more": False,
        "source": "cen_msaa",
        "index_base": 1,
    }

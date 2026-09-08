"""Spatial clustering of text nodes inside a grid bbox (legacy COBISGrid fallback)."""
from __future__ import annotations

from typing import Any

from detection.uia_text import get_cell_text
from detection.uia_tree import _walk_control_tree, _wrap_raw

_TEXT_ROLES = frozenset({"text", "dataitem", "listitem", "button", "edit"})


def _inside(rect: dict[str, int], x: int, y: int) -> bool:
    return (
        rect["x"] <= x <= rect["x"] + rect["w"]
        and rect["y"] <= y <= rect["y"] + rect["h"]
    )


def collect_spatial_grid(raw, element: dict[str, Any], y_tolerance: int = 8) -> dict[str, Any]:
    """Cluster visible text nodes by Y band into rows."""
    gx = int(element.get("x") or 0)
    gy = int(element.get("y") or 0)
    gw = int(element.get("width") or element.get("w") or 0)
    gh = int(element.get("height") or element.get("h") or 0)
    if gw <= 0 or gh <= 0:
        return {}

    rect = {"x": gx, "y": gy, "w": gw, "h": gh}
    nodes: list[dict[str, Any]] = []

    for child in _walk_control_tree(raw):
        det = _wrap_raw(child)
        if not det:
            continue
        role = (det.role or "").lower()
        if role not in _TEXT_ROLES and not (det.name or "").strip():
            continue
        cx = int(det.x) + int(det.width) // 2
        cy = int(det.y) + int(det.height) // 2
        if not _inside(rect, cx, cy):
            continue
        text = (get_cell_text(child) or det.name or getattr(det, "value", "") or "").strip()
        if not text:
            continue
        nodes.append({"x": int(det.x), "y": int(det.y), "text": text})

    if not nodes:
        return {}

    nodes.sort(key=lambda n: (n["y"], n["x"]))
    bands: list[list[dict[str, Any]]] = []
    for node in nodes:
        if not bands or abs(node["y"] - bands[-1][0]["y"]) > y_tolerance:
            bands.append([node])
        else:
            bands[-1].append(node)

    rows: list[list[str]] = []
    for band in bands:
        band.sort(key=lambda n: n["x"])
        rows.append([n["text"] for n in band])

    if len(rows) >= 2:
        headers = rows[0]
        data = rows[1:]
    else:
        width = max(len(r) for r in rows)
        headers = [f"col_{i}" for i in range(width)]
        data = rows

    return {
        "headers": headers,
        "rows": data,
        "row_count": len(data),
        "total_rows": len(data),
        "offset": 0,
        "limit": len(data),
        "has_more": False,
        "source": "cen_spatial_uia",
        "index_base": 1,
    }

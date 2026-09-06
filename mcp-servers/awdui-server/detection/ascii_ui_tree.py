"""Containment tree + occlusion pruning for ASCII UI rendering."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


def _area(elem: dict[str, Any]) -> int:
    return max(0, int(elem.get("width") or 0)) * max(0, int(elem.get("height") or 0))


def _bounds(elem: dict[str, Any]) -> tuple[int, int, int, int, int, int]:
    x = int(elem.get("x") or 0)
    y = int(elem.get("y") or 0)
    w = int(elem.get("width") or 0)
    h = int(elem.get("height") or 0)
    return x, y, w, h, x + w, y + h


def _center_inside(outer: dict[str, Any], inner: dict[str, Any], tol: int = 2) -> bool:
    ox, oy, _, _, ox2, oy2 = _bounds(outer)
    ix, iy, iw, ih, _, _ = _bounds(inner)
    if iw <= 0 or ih <= 0:
        return False
    cx = ix + iw // 2
    cy = iy + ih // 2
    return (ox - tol) <= cx <= (ox2 + tol) and (oy - tol) <= cy <= (oy2 + tol)


def _fully_covers(outer: dict[str, Any], inner: dict[str, Any], tol: int = 1) -> bool:
    ox, oy, _, _, ox2, oy2 = _bounds(outer)
    ix, iy, _, _, ix2, iy2 = _bounds(inner)
    if ix2 <= ix or iy2 <= iy:
        return False
    return ox <= ix + tol and oy <= iy + tol and ox2 >= ix2 - tol and oy2 >= iy2 - tol


def _role_priority(role: str) -> int:
    """Higher = prefer keeping when boxes overlap."""
    r = (role or "").strip().lower()
    if r == "button":
        return 5
    if r in ("edit", "combobox", "checkbox", "radiobutton"):
        return 4
    if r in ("listitem", "menuitem", "tabitem", "hyperlink"):
        return 3
    if r == "text":
        return 2
    return 1


@dataclass
class AsciiTreeNode:
    elem: dict[str, Any]
    children: list[AsciiTreeNode] = field(default_factory=list)
    parent: Optional[AsciiTreeNode] = None


def build_containment_forest(elements: list[dict[str, Any]]) -> list[AsciiTreeNode]:
    """Assign each element to the smallest larger bbox that contains its center."""
    nodes = [AsciiTreeNode(elem=dict(e)) for e in elements]
    if not nodes:
        return []

    for i, node in enumerate(nodes):
        best: Optional[AsciiTreeNode] = None
        best_area = 0
        ai = _area(node.elem)
        for j, other in enumerate(nodes):
            if i == j:
                continue
            aj = _area(other.elem)
            if aj <= ai:
                continue
            if _center_inside(other.elem, node.elem):
                if best is None or aj < best_area:
                    best = other
                    best_area = aj
        if best is not None:
            best.children.append(node)
            node.parent = best

    roots = [n for n in nodes if n.parent is None]
    _sort_children_dfs(roots)
    return roots


def _sort_children_dfs(nodes: list[AsciiTreeNode]) -> None:
    for node in nodes:
        node.children.sort(
            key=lambda n: (int(n.elem.get("y") or 0), int(n.elem.get("x") or 0))
        )
        _sort_children_dfs(node.children)


def _has_drawable_descendant(node: AsciiTreeNode, drawable_roles: frozenset[str]) -> bool:
    role = (node.elem.get("role") or "").strip()
    if role in drawable_roles:
        return True
    return any(_has_drawable_descendant(ch, drawable_roles) for ch in node.children)


def collect_drawable_elements(
    roots: list[AsciiTreeNode],
    drawable_roles: frozenset[str],
    occlusion_prune: bool = True,
) -> list[dict[str, Any]]:
    """DFS with sibling occlusion; keep drawable leaves (no drawable child inside)."""
    drawables: list[dict[str, Any]] = []

    def walk(node: AsciiTreeNode, siblings_after: list[AsciiTreeNode], parent_visible: bool) -> None:
        occluded = False
        if occlusion_prune and parent_visible and siblings_after:
            for sib in siblings_after:
                if _fully_covers(sib.elem, node.elem):
                    occluded = True
                    break
        visible = parent_visible and not occluded

        role = (node.elem.get("role") or "").strip()
        is_drawable_role = role in drawable_roles
        has_inner = any(
            _has_drawable_descendant(ch, drawable_roles) for ch in node.children
        )

        if visible and is_drawable_role and not has_inner:
            drawables.append(node.elem)

        if visible:
            for idx, child in enumerate(node.children):
                walk(child, node.children[idx + 1 :], True)

    for idx, root in enumerate(roots):
        walk(root, roots[idx + 1 :], True)

    return _dedupe_overlaps(drawables)


def _dedupe_overlaps(elements: list[dict[str, Any]], iou_threshold: float = 0.65) -> list[dict[str, Any]]:
    """Drop lower-priority elements when two boxes overlap heavily."""
    if len(elements) < 2:
        return elements

    kept: list[dict[str, Any]] = []
    for elem in sorted(elements, key=lambda e: (-_role_priority(e.get("role") or ""), _area(e))):
        drop = False
        for other in kept:
            if _overlap_ratio(elem, other) >= iou_threshold:
                if _role_priority(elem.get("role") or "") < _role_priority(other.get("role") or ""):
                    drop = True
                    break
                if _role_priority(elem.get("role") or "") == _role_priority(other.get("role") or ""):
                    if _area(elem) > _area(other):
                        drop = True
                        break
        if not drop:
            kept.append(elem)
    kept.sort(key=lambda e: _area(e))
    return kept


def _overlap_ratio(a: dict[str, Any], b: dict[str, Any]) -> float:
    ax, ay, _, _, ax2, ay2 = _bounds(a)
    bx, by, _, _, bx2, by2 = _bounds(b)
    ix1, iy1 = max(ax, bx), max(ay, by)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    union = _area(a) + _area(b) - inter
    return inter / union if union > 0 else 0.0


def prepare_elements_for_render(
    elements: list[dict[str, Any]],
    drawable_roles: frozenset[str],
    occlusion_prune: bool = True,
) -> list[dict[str, Any]]:
    """Build containment forest and return leaf drawables in paint order (small on top)."""
    if not elements:
        return []
    roots = build_containment_forest(elements)
    drawables = collect_drawable_elements(roots, drawable_roles, occlusion_prune=occlusion_prune)
    if drawables:
        return drawables
    # Fallback: flat list sorted by area when tree yields nothing
    flat = [e for e in elements if (e.get("role") or "").strip() in drawable_roles]
    flat.sort(key=_area)
    return flat

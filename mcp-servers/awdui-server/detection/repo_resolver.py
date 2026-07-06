"""Hierarchical object repository resolution with QTP-style Smart Identification."""
from __future__ import annotations

from typing import Any, Callable, Optional

from detection.object_repository import get_object, parse_repo_path
from detection.winforms_map import infer_swf_class, profile_for, role_for_swf


def _elem_inside_parent(elem: dict, parent: dict) -> bool:
    cx = elem.get("x", 0) + elem.get("width", 0) // 2
    cy = elem.get("y", 0) + elem.get("height", 0) // 2
    px, py = parent.get("x", 0), parent.get("y", 0)
    pw, ph = parent.get("width", 0), parent.get("height", 0)
    if pw <= 0 or ph <= 0:
        return True
    return px <= cx <= px + pw and py <= cy <= py + ph


def _filter_by_parent(candidates: list[dict], parent_elem: Optional[dict]) -> list[dict]:
    if not parent_elem or not candidates:
        return candidates
    scoped = [e for e in candidates if _elem_inside_parent(e, parent_elem)]
    return scoped if scoped else candidates


def _ident_tier_props(ident: dict, tier: str) -> dict[str, str]:
    return {k: v for k, v in ident.get(tier, {}).items() if v}


def _ordinal_index(ident: dict, default: int = 0) -> int:
    ordinal = ident.get("ordinal", {})
    for key in ("index", "location", "creationtime"):
        if key in ordinal:
            try:
                return int(ordinal[key])
            except (TypeError, ValueError):
                pass
    return default


def _find_with_props(
    orch,
    props: dict[str, str],
    *,
    window_title: Optional[str],
    index: int = 0,
    parent_elem: Optional[dict] = None,
) -> Optional[dict]:
    result = orch.find_elements(
        name=props.get("name"),
        role=props.get("role"),
        automation_id=props.get("automation_id"),
        class_name=props.get("class_name"),
        window_title=window_title,
        index=index,
    )
    if not result.get("found"):
        return None
    elements = result.get("elements", [])
    elements = _filter_by_parent(elements, parent_elem)
    if not elements:
        return None
    idx = min(index, len(elements) - 1) if index > 0 else 0
    elem = elements[idx]
    elem["backend_used"] = result.get("backend_used", "uia")
    return elem


def _smart_identify(
    orch,
    obj: dict,
    *,
    window_title: Optional[str],
    parent_elem: Optional[dict],
    template_matcher: Optional[Callable[[str, Optional[str]], Optional[dict]]] = None,
    ocr_finder: Optional[Callable[[str, Optional[str]], list[dict]]] = None,
) -> tuple[Optional[dict], str]:
    """QTP Smart ID: mandatory → assistive → smart props → ordinal → template → OCR."""
    ident = obj.get("identification", {})
    swf_class = obj.get("class", "SwfObject")

    tiers = [
        ("mandatory", _ident_tier_props(ident, "mandatory")),
        ("mandatory+assistive", {**_ident_tier_props(ident, "mandatory"), **_ident_tier_props(ident, "assistive")}),
    ]
    for tier_name, props in tiers:
        if props:
            elem = _find_with_props(
                orch, props, window_title=window_title,
                index=_ordinal_index(ident), parent_elem=parent_elem,
            )
            if elem:
                return elem, f"repository:{tier_name}"

    smart = _ident_tier_props(ident, "smart")
    for prop, val in smart.items():
        query = {"role": role_for_swf(swf_class) or ident.get("assistive", {}).get("role", "")}
        if prop in ("name", "text"):
            query["name"] = val
        elif prop in ("automation_id", "class_name", "role"):
            query[prop] = val
        else:
            query["name"] = val
        elem = _find_with_props(
            orch, query, window_title=window_title,
            index=_ordinal_index(ident), parent_elem=parent_elem,
        )
        if elem:
            return elem, f"smart_id:{prop}"

    snapshots = obj.get("snapshots", {}).get("latest", {})
    template = snapshots.get("images", {}).get("template")
    if template and template_matcher:
        match = template_matcher(template, window_title)
        if match:
            return match.get("element"), "repository:template"

    text = (
        ident.get("mandatory", {}).get("name")
        or ident.get("assistive", {}).get("name")
        or ident.get("smart", {}).get("name")
        or ident.get("smart", {}).get("text")
        or obj.get("_object_name", "")
    )
    if text and ocr_finder:
        matches = ocr_finder(text, window_title)
        matches = _filter_by_parent(matches, parent_elem)
        if matches:
            return matches[0], "smart_id:ocr"

    return None, ""


def resolve_parent_chain(
    repo: dict,
    window_key: str,
    chain: list[str],
    orch,
    window_title: Optional[str],
    template_matcher=None,
    ocr_finder=None,
) -> tuple[Optional[dict], Optional[dict], str]:
    """Resolve intermediate parents; return (leaf_obj_meta, parent_element, error)."""
    if len(chain) <= 1:
        return None, None, ""

    parent_elem: Optional[dict] = None
    objects = repo.get("windows", {}).get(window_key, {}).get("objects", {})

    for name in chain[:-1]:
        parent_obj = objects.get(name)
        if not parent_obj:
            return None, None, f"Parent object '{name}' not in repository"
        parent_obj = dict(parent_obj)
        parent_obj["_object_name"] = name
        parent_obj["_window_key"] = window_key

        elem, method = _smart_identify(
            orch, parent_obj,
            window_title=window_title,
            parent_elem=parent_elem,
            template_matcher=template_matcher,
            ocr_finder=ocr_finder,
        )
        if not elem:
            return None, None, f"Could not resolve parent '{name}' in chain"
        parent_elem = elem

    return None, parent_elem, ""


def resolve_repo_object(
    repo: dict,
    repo_path: str,
    orch,
    *,
    window_title: Optional[str] = None,
    template_matcher=None,
    ocr_finder=None,
) -> dict[str, Any]:
    """
    Resolve a repository object (supports nested paths like frmMain/tabDatos/txtNombre).
    Returns {found, element, method, obj, repo_path, error}.
    """
    try:
        window_key, chain = parse_repo_path(repo_path)
    except ValueError as e:
        return {"found": False, "error": str(e)}

    obj = get_object(repo, repo_path)
    if not obj:
        return {"found": False, "error": f"Object '{repo_path}' not in repository"}

    obj = dict(obj)

    parent_elem: Optional[dict] = None
    if len(chain) > 1:
        _, parent_elem, err = resolve_parent_chain(
            repo, window_key, chain, orch, window_title,
            template_matcher=template_matcher,
            ocr_finder=ocr_finder,
        )
        if err:
            return {"found": False, "error": err}

    elem, method = _smart_identify(
        orch, obj,
        window_title=window_title,
        parent_elem=parent_elem,
        template_matcher=template_matcher,
        ocr_finder=ocr_finder,
    )
    if elem:
        return {
            "found": True,
            "element": elem,
            "method": method,
            "obj": obj,
            "repo_path": repo_path,
            "swf_class": obj.get("class") or infer_swf_class(elem.get("role", ""), elem.get("class_name", "")),
        }
    return {"found": False, "error": f"Could not resolve '{repo_path}' via Smart Identification"}


def identification_for_capture(elem: dict, swf_class: str, parent: str = "") -> dict[str, Any]:
    from detection.winforms_map import build_identification
    ident = build_identification(elem, swf_class)
    meta = {
        "class": swf_class,
        "parent": parent,
        "identification": ident,
    }
    prof = profile_for(swf_class)
    meta["allowed_methods"] = prof.get("methods", [])
    return meta

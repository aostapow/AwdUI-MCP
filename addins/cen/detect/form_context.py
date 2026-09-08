"""Detect active CEN form / product context from window and elements."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional


@lru_cache(maxsize=1)
def _load_modules() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "knowledge" / "modules.json"
    return json.loads(path.read_text(encoding="utf-8"))


def detect_product(window_title: str = "", process_name: str = "") -> dict[str, Any]:
    cfg = _load_modules()
    title = (window_title or "").lower()
    proc = (process_name or "").lower()
    matches = []
    for prod in cfg.get("products", []):
        score = 0.0
        if prod["code"].lower() in title or prod["prefix"].lower() in title:
            score += 0.5
        if prod.get("alias", "").lower() in title:
            score += 0.3
        if prod["dll"].lower() in proc:
            score += 0.8
        if score > 0:
            matches.append({**prod, "score": score})
    matches.sort(key=lambda m: m["score"], reverse=True)
    return {
        "product": matches[0] if matches else None,
        "candidates": matches[:3],
        "shell": cfg.get("shell", {}),
    }


def detect_form_class(elements: list[dict[str, Any]], window_title: str = "") -> dict[str, Any]:
    cfg = _load_modules()
    title = window_title or ""
    class_hints: list[str] = []

    for el in elements:
        cn = (el.get("class_name") or "")
        if "COBISFuncionalityView" in cn or cn.endswith("Class"):
            class_hints.append(cn)
        aid = (el.get("automation_id") or el.get("name") or "")
        if re.match(r"^F(TRAN|TRA|Tra)\d+", aid, re.I):
            class_hints.append(aid)

    form_type = "unknown"
    for pattern in cfg.get("form_naming", {}).get("transaction", []):
        if re.search(pattern, title, re.I) or any(re.search(pattern, h, re.I) for h in class_hints):
            form_type = "transaction"
            break
    for sf in cfg.get("shared_forms", []):
        if sf["id"] in title.lower() or any(sf["class"] in h for h in class_hints):
            form_type = "shared_" + sf["id"]
            break

    has_pforma = any(
        (el.get("name") or "").lower() == "pforma"
        or "ultragroupbox" in (el.get("class_name") or "").lower()
        for el in elements
    )
    has_toolbar = any("cmdboton" in (el.get("name") or el.get("automation_id") or "").lower() for el in elements)
    grids = [el.get("name") or el.get("automation_id") for el in elements if (el.get("name") or "").lower().startswith("grd")]

    return {
        "form_type": form_type,
        "window_title": title,
        "has_pforma": has_pforma,
        "has_toolbar": has_toolbar,
        "grid_names": [g for g in grids if g][:10],
        "class_hints": class_hints[:5],
    }


def build_form_context(
    window_title: Optional[str] = None,
    elements: Optional[list[dict[str, Any]]] = None,
    process_name: str = "",
) -> dict[str, Any]:
    from tools.target_window import get_target

    title = (window_title or get_target() or "").strip()
    elems = elements or []
    return {
        "success": True,
        "window_title": title,
        "product": detect_product(title, process_name),
        "form": detect_form_class(elems, title),
    }

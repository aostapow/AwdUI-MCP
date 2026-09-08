"""Load and query machine-extracted + curated form catalog."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional


def _knowledge_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "knowledge"


@lru_cache(maxsize=1)
def _load_catalog() -> dict[str, Any]:
    catalog_path = _knowledge_dir() / "forms_catalog.json"
    curated_path = _knowledge_dir() / "forms_index.json"
    if catalog_path.is_file():
        return json.loads(catalog_path.read_text(encoding="utf-8"))
    if curated_path.is_file():
        data = json.loads(curated_path.read_text(encoding="utf-8"))
        return {"version": 1, "forms": data.get("forms", [])}
    return {"version": 1, "forms": []}


@lru_cache(maxsize=1)
def _load_index() -> dict[str, Any]:
    path = _knowledge_dir() / "forms_catalog_index.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def catalog_stats() -> dict[str, Any]:
    cat = _load_catalog()
    idx = _load_index()
    return {
        "success": True,
        "total_forms": cat.get("total") or len(cat.get("forms") or []),
        "extracted_count": cat.get("extracted_count"),
        "curated_count": cat.get("curated_count"),
        "by_product": idx.get("by_product") or {},
        "index_loaded": bool(idx),
    }


def get_popup_hints(form_id: str) -> dict[str, Any]:
    path = _knowledge_dir() / "popups_registry.json"
    if not path.is_file():
        return {"success": False, "error": "popups_registry.json not found"}
    data = json.loads(path.read_text(encoding="utf-8"))
    pops = (data.get("by_host_form") or {}).get(form_id) or []
    return {
        "success": True,
        "form_id": form_id,
        "popups": pops,
        "top_popups": data.get("top_popups", [])[:10],
    }


def list_forms(
    prefix: str = "",
    product: str = "",
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    idx = _load_index()
    if idx.get("forms") and prefix and not product:
        prefix_l = prefix.lower()
        filtered_idx = [
            e for e in idx["forms"] if (e.get("id") or "").lower().startswith(prefix_l)
        ]
        total = len(filtered_idx)
        slice_ = filtered_idx[offset : offset + limit]
        return {
            "success": True,
            "total": total,
            "offset": offset,
            "limit": limit,
            "forms": slice_,
            "source": "index",
            "catalog_meta": catalog_stats(),
        }

    forms = _load_catalog().get("forms") or []
    prefix_l = prefix.lower()
    filtered = []
    for form in forms:
        fid = form.get("id", "")
        if prefix and not fid.lower().startswith(prefix_l):
            continue
        if product and (form.get("product") or "").upper() != product.upper():
            continue
        filtered.append(
            {
                "id": fid,
                "product": form.get("product"),
                "toolbar_count": len(form.get("toolbar") or {}),
                "grids": (form.get("grids") or [])[:3],
                "curated": bool(form.get("curated")),
            }
        )
    total = len(filtered)
    return {
        "success": True,
        "total": total,
        "offset": offset,
        "limit": limit,
        "forms": filtered[offset : offset + limit],
        "catalog_meta": {
            k: _load_catalog().get(k)
            for k in ("extracted_count", "curated_count", "total")
            if k in _load_catalog()
        },
    }


def get_form_profile(form_id: str) -> dict[str, Any]:
    fid = (form_id or "").strip()
    if not fid:
        return {"success": False, "error": "form_id required"}
    for form in _load_catalog().get("forms") or []:
        if form.get("id", "").lower() == fid.lower():
            return {"success": True, "form": form}
    return {"success": False, "error": f"form {fid} not in catalog"}


def search_forms(query: str, limit: int = 20) -> dict[str, Any]:
    q = (query or "").lower()
    hits = []
    for form in _load_catalog().get("forms") or []:
        fid = (form.get("id") or "").lower()
        src = (form.get("source") or "").lower()
        score = 0.0
        if fid == q:
            score = 1.0
        elif fid.startswith(q):
            score = 0.8
        elif q in fid:
            score = 0.6
        elif q in src:
            score = 0.4
        if score > 0:
            hits.append({"score": score, "form": form})
    hits.sort(key=lambda h: h["score"], reverse=True)
    return {
        "success": True,
        "query": query,
        "count": len(hits),
        "results": [{"score": h["score"], **h["form"]} for h in hits[:limit]],
    }

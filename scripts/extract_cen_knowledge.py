#!/usr/bin/env python3
"""Full CEN static knowledge extraction: forms, index, messages, popups."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

# Reuse forms extractor
from extract_cen_forms_index import (
    _normalize_form_id,
    _parse_controls,
    _parse_toolbar,
    _product_from_path,
    extract_from_roots,
    merge_with_curated,
)

RE_FORM_CLASS = re.compile(r"partial\s+class\s+(\w+)")
RE_BB_TEXT = re.compile(r"this\.(bb_\w+)\.Text\s*=\s*\"([^\"]+)\"", re.MULTILINE)
RE_USER_CONTROL = re.compile(
    r"this\.(cmdMoneda_UserControl\w*)\s*=\s*new\s+[^;]+cmdMoneda_UserControl",
    re.MULTILINE,
)
RE_TAB = re.compile(
    r"this\.(MhTab\w*|mht\w*|tbPar\w*)\s*=\s*new\s+[^;]+COBISTabControl",
    re.MULTILINE,
)
RE_RADIO = re.compile(
    r"this\.(?:_)?(opt\w+)_(\d+)\.Text\s*=\s*\"([^\"]+)\"",
    re.MULTILINE,
)
RE_MSG = re.compile(r"COBISMessageBox\.Show\(\s*\"([^\"]{8,200})\"", re.MULTILINE)
RE_POPUP = re.compile(
    r"([A-Za-z][\w]*(?:Class)?)\.DefInstance\.ShowPopup",
    re.MULTILINE,
)
RE_F5_BLOCK = re.compile(
    r"if\s*\([^)]*KeyCode\s*==\s*Keys\.F5",
    re.MULTILINE,
)


def _parse_designer_extras(text: str) -> dict[str, Any]:
    bb: dict[str, str] = {}
    for name, caption in RE_BB_TEXT.findall(text):
        bb[name] = caption.replace("\\", "")
    user_controls = sorted(set(RE_USER_CONTROL.findall(text)))
    tabs = sorted(set(RE_TAB.findall(text)))
    radios: dict[str, dict[str, str]] = defaultdict(dict)
    for group, idx, caption in RE_RADIO.findall(text):
        radios[group][idx] = caption.replace("\\", "")
    return {
        "bb_buttons": bb,
        "user_controls": user_controls[:6],
        "tabs": tabs[:6],
        "radios": {k: dict(sorted(v.items())) for k, v in list(radios.items())[:4]},
    }


def _parse_cs_companion(cs_path: Path) -> dict[str, Any]:
    if not cs_path.is_file():
        return {"messages": [], "popups": [], "has_f5_handler": False}
    try:
        text = cs_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return {"messages": [], "popups": [], "has_f5_handler": False}
    messages = list(dict.fromkeys(RE_MSG.findall(text)))[:30]
    popups = list(dict.fromkeys(RE_POPUP.findall(text)))[:20]
    return {
        "messages": messages,
        "popups": popups,
        "has_f5_handler": bool(RE_F5_BLOCK.search(text)),
    }


def enrich_forms(forms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched = []
    for form in forms:
        src = Path(form.get("source") or "")
        text = ""
        if src.is_file():
            text = src.read_text(encoding="utf-8", errors="ignore")
        extras = _parse_designer_extras(text)
        cs_path = src.with_name(src.name.replace(".Designer.cs", ".cs"))
        cs_data = _parse_cs_companion(cs_path)
        entry = {**form, **extras, **cs_data}
        if cs_data.get("has_f5_handler") and not entry.get("f5_fields"):
            entry["f5_capable"] = True
        enriched.append(entry)
    return enriched


def build_catalog_index(catalog: dict[str, Any]) -> dict[str, Any]:
    by_product: Counter[str] = Counter()
    entries = []
    for form in catalog.get("forms") or []:
        prod = form.get("product") or "?"
        by_product[prod] += 1
        captions = [
            (btn or {}).get("text", "")
            for btn in (form.get("toolbar") or {}).values()
            if isinstance(btn, dict)
        ]
        entries.append(
            {
                "id": form.get("id"),
                "product": prod,
                "toolbar_captions": [c for c in captions if c][:12],
                "grid_count": len(form.get("grids") or []),
                "has_f5": bool(form.get("f5_capable") or form.get("has_f5_handler")),
                "curated": bool(form.get("curated")),
            }
        )
    return {
        "version": 1,
        "total": len(entries),
        "by_product": dict(by_product.most_common()),
        "forms": entries,
    }


def build_messages_catalog(forms: list[dict[str, Any]]) -> dict[str, Any]:
    all_msgs: Counter[str] = Counter()
    by_category: dict[str, list[str]] = defaultdict(list)
    keywords = {
        "validation": ["mandatorio", "obligatorio", "incorrecto", "error", "fuera de rango"],
        "confirm": ["seguro", "desea", "continuar", "eliminar"],
        "success": ["exitosa", "terminado", "generado", "correctamente"],
        "empty": ["no existen", "no hay", "sin datos"],
        "security": ["no autorizada", "no autorizado", "permiso"],
    }
    for form in forms:
        for msg in form.get("messages") or []:
            all_msgs[msg] += 1
    for msg, _count in all_msgs.most_common(500):
        low = msg.lower()
        cat = "other"
        for category, kws in keywords.items():
            if any(k in low for k in kws):
                cat = category
                break
        if msg not in by_category[cat]:
            by_category[cat].append(msg)
    return {
        "version": 1,
        "unique_count": len(all_msgs),
        "top_messages": [{"text": m, "count": c} for m, c in all_msgs.most_common(80)],
        "by_category": {k: v[:40] for k, v in by_category.items()},
    }


def build_popups_registry(forms: list[dict[str, Any]]) -> dict[str, Any]:
    popup_forms: Counter[str] = Counter()
    by_host: dict[str, list[str]] = {}
    for form in forms:
        pops = form.get("popups") or []
        if pops:
            by_host[form["id"]] = pops
            for p in pops:
                popup_forms[p] += 1
    return {
        "version": 1,
        "unique_popups": len(popup_forms),
        "top_popups": [{"class": k, "count": v} for k, v in popup_forms.most_common(60)],
        "by_host_form": by_host,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract full CEN knowledge bundle")
    parser.add_argument("roots", nargs="+", help="Module roots (e.g. Productos Nuevo)")
    parser.add_argument(
        "--knowledge-dir",
        default=str(Path(__file__).resolve().parents[1] / "addins" / "cen" / "knowledge"),
    )
    args = parser.parse_args()
    knowledge = Path(args.knowledge_dir)
    curated = knowledge / "forms_index.json"

    roots = [Path(p) for p in args.roots]
    extracted = enrich_forms(extract_from_roots(roots))
    catalog = merge_with_curated(extracted, curated)

    index = build_catalog_index(catalog)
    messages = build_messages_catalog(catalog["forms"])
    popups = build_popups_registry(catalog["forms"])

    paths = {
        "forms_catalog.json": catalog,
        "forms_catalog_index.json": index,
        "messages_catalog.json": messages,
        "popups_registry.json": popups,
    }
    for name, data in paths.items():
        out = knowledge / name
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {name} ({data.get('total') or data.get('unique_count') or len(data.get('forms', []))} records)")

    print(
        f"Done: {catalog['total']} forms, "
        f"{messages['unique_count']} unique messages, "
        f"{popups['unique_popups']} popup classes"
    )


if __name__ == "__main__":
    main()

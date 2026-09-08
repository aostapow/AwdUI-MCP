#!/usr/bin/env python3
"""Extract CEN form metadata from *.Designer.cs into forms_catalog.json."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

PRODUCT_FROM_PATH = [
    (re.compile(r"\.ADMIN\.", re.I), "ADM"),
    (re.compile(r"\.TADMIN\.", re.I), "TAD"),
    (re.compile(r"\.REC\.", re.I), "REC"),
    (re.compile(r"\.CRE\.", re.I), "CRE"),
    (re.compile(r"\.PFI\.", re.I), "PFI"),
    (re.compile(r"\.CON\.", re.I), "CON"),
    (re.compile(r"\.CTR\.", re.I), "CTR"),
    (re.compile(r"Pasivas", re.I), "TAD"),
    (re.compile(r"Recauda", re.I), "REC"),
    (re.compile(r"Concentrador", re.I), "CTR"),
]

RE_CMD_TEXT = re.compile(
    r"this\.(?:_)?cmdBoton_(\d+)\.Text\s*=\s*\"([^\"]+)\"",
    re.MULTILINE,
)
RE_CMD_TEXT_ALT = re.compile(
    r"this\.cmdBoton\[(\d+)\]\.Text\s*=\s*\"([^\"]+)\"",
    re.MULTILINE,
)
RE_CMD_TAG = re.compile(
    r"this\.(?:_)?cmdBoton_(\d+)\.Tag\s*=\s*\"([^\"]+)\"",
    re.MULTILINE,
)
RE_FORM_CLASS = re.compile(r"partial\s+class\s+(\w+)")
RE_CONTROL = re.compile(
    r"this\.(\w+)\s*=\s*new\s+(?:COBISCorp\.[^;]+|System\.Windows\.Forms\.)"
    r"(COBISGrid|COBISSpread|COBISValidTextBox|COBISMaskedInBox|COBISMaskedTextBox|"
    r"TriStateTreeView|COBISMSOutline|COBISTabControl)",
    re.MULTILINE,
)
RE_NAME_FIELD = re.compile(
    r"public\s+(?:System\.Windows\.Forms\.)?"
    r"(?:COBISValidTextBox|COBISMaskedInBox|COBISMaskedTextBox|COBISGrid|COBISSpread|"
    r"TriStateTreeView|COBISMSOutline)\s+(\w+)",
)


def _normalize_form_id(class_name: str) -> str:
    name = class_name
    for suffix in ("Class", "View"):
        if name.endswith(suffix) and len(name) > len(suffix):
            name = name[: -len(suffix)]
    return name


def _product_from_path(path: Path) -> str:
    text = str(path)
    for pattern, code in PRODUCT_FROM_PATH:
        if pattern.search(text):
            return code
    return ""


def _parse_toolbar(text: str) -> dict[str, dict[str, str]]:
    toolbar: dict[str, dict[str, str]] = {}
    for pattern in (RE_CMD_TEXT, RE_CMD_TEXT_ALT):
        for idx, caption in pattern.findall(text):
            toolbar[idx] = {"text": caption.replace("\\", "")}
    for idx, tag in RE_CMD_TAG.findall(text):
        toolbar.setdefault(idx, {})["tag"] = tag
    return dict(sorted(toolbar.items(), key=lambda kv: int(kv[0])))


def _parse_controls(text: str) -> dict[str, list[str]]:
    grids: list[str] = []
    fields: list[str] = []
    trees: list[str] = []
    outlines: list[str] = []
    for name, ctype in RE_CONTROL.findall(text):
        if ctype in ("COBISGrid", "COBISSpread"):
            grids.append(name)
        elif ctype in ("COBISValidTextBox", "COBISMaskedInBox", "COBISMaskedTextBox"):
            fields.append(name)
        elif ctype == "TriStateTreeView":
            trees.append(name)
        elif ctype == "COBISMSOutline":
            outlines.append(name)
    for name in RE_NAME_FIELD.findall(text):
        low = name.lower()
        if low.startswith("grd") and name not in grids:
            grids.append(name)
        elif low.startswith(("txt", "msk")) and name not in fields:
            fields.append(name)
        elif low.startswith(("tv", "trv")) and name not in trees:
            trees.append(name)
        elif low.startswith("otl") and name not in outlines:
            outlines.append(name)
    return {
        "grids": sorted(set(grids))[:12],
        "key_fields": sorted(set(fields))[:20],
        "trees": sorted(set(trees))[:6],
        "outlines": sorted(set(outlines))[:6],
    }


def extract_from_roots(roots: list[Path], views_only: bool = True) -> list[dict[str, Any]]:
    forms: list[dict[str, Any]] = []
    seen: set[str] = set()

    for root in roots:
        if not root.is_dir():
            continue
        glob = "**/Views/*.Designer.cs" if views_only else "**/*.Designer.cs"
        for designer in root.glob(glob):
            try:
                text = designer.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if "cmdBoton" not in text and "ToolStripButton" not in text:
                continue
            form_match = RE_FORM_CLASS.search(text)
            if not form_match:
                continue
            class_name = form_match.group(1)
            form_id = _normalize_form_id(class_name)
            if form_id in seen:
                continue
            toolbar = _parse_toolbar(text)
            if not toolbar:
                continue
            seen.add(form_id)
            controls = _parse_controls(text)
            forms.append(
                {
                    "id": form_id,
                    "class_name": class_name,
                    "product": _product_from_path(designer),
                    "source": str(designer),
                    "toolbar": toolbar,
                    **controls,
                }
            )
    forms.sort(key=lambda f: f["id"])
    return forms


def merge_with_curated(
    extracted: list[dict[str, Any]],
    curated_path: Path,
) -> dict[str, Any]:
    curated: list[dict[str, Any]] = []
    if curated_path.is_file():
        curated = json.loads(curated_path.read_text(encoding="utf-8")).get("forms", [])
    by_id = {f["id"]: f for f in extracted}
    for hand in curated:
        fid = hand["id"]
        if fid in by_id:
            merged = {**by_id[fid], **hand}
            merged["curated"] = True
            by_id[fid] = merged
        else:
            hand["curated"] = True
            by_id[fid] = hand
    forms = sorted(by_id.values(), key=lambda f: f["id"])
    return {
        "version": 1,
        "extracted_count": len(extracted),
        "curated_count": len(curated),
        "total": len(forms),
        "forms": forms,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract CEN form catalog from Designer.cs")
    parser.add_argument("roots", nargs="+", help="Module roots to scan")
    parser.add_argument(
        "--out",
        default=str(
            Path(__file__).resolve().parents[1]
            / "addins"
            / "cen"
            / "knowledge"
            / "forms_catalog.json"
        ),
    )
    parser.add_argument(
        "--curated",
        default=str(
            Path(__file__).resolve().parents[1]
            / "addins"
            / "cen"
            / "knowledge"
            / "forms_index.json"
        ),
    )
    parser.add_argument("--all-designers", action="store_true")
    args = parser.parse_args()
    roots = [Path(p) for p in args.roots]
    extracted = extract_from_roots(roots, views_only=not args.all_designers)
    catalog = merge_with_curated(extracted, Path(args.curated))
    out_path = Path(args.out)
    out_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Extracted {len(extracted)} forms, catalog total {catalog['total']} -> {out_path}")


if __name__ == "__main__":
    main()

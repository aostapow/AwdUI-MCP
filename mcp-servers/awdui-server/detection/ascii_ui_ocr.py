"""OCR enrichment for ASCII UI view (unnamed Image/Custom/controls)."""
from __future__ import annotations

import os
import tempfile
from typing import Any, Optional

from PIL import Image, ImageOps

_OCR_ROI_ROLES = frozenset(
    {
        "image",
        "custom",
        "pane",
        "group",
        "graphic",
        "imagebutton",
        "unknown",
        "",
    }
)


def _norm_role(role: str) -> str:
    s = (role or "").strip().lower().lstrip("ax")
    return s.replace("_", "").replace("-", "").replace(" ", "")


def _needs_ocr_enrich(elem: dict[str, Any]) -> bool:
    if (elem.get("name") or "").strip():
        return False
    if (elem.get("value") or "").strip():
        return False
    role = _norm_role(elem.get("role") or "")
    if role in _OCR_ROI_ROLES:
        return True
    w = int(elem.get("width") or 0)
    h = int(elem.get("height") or 0)
    return w >= 12 and h >= 12 and role in ("button", "text", "listitem")


def _ocr_pil_image(img: Image.Image, upscale: int = 2) -> list[dict[str, Any]]:
    work = img.convert("RGB")
    if upscale > 1:
        work = work.resize(
            (max(1, work.width * upscale), max(1, work.height * upscale)),
            Image.LANCZOS,
        )
    try:
        work = ImageOps.autocontrast(work)
    except Exception:
        pass
    path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            path = tmp.name
            work.save(path)
        from tools.ocr import _rapid_ocr_on_image

        words = _rapid_ocr_on_image(path)
        if upscale > 1:
            inv = 1.0 / upscale
            for w in words:
                w["x"] = int(round(w["x"] * inv))
                w["y"] = int(round(w["y"] * inv))
                w["width"] = int(round(w["width"] * inv))
                w["height"] = int(round(w["height"] * inv))
        return words
    finally:
        if path:
            try:
                os.remove(path)
            except OSError:
                pass
    return []


def capture_window_image(
    window_title: Optional[str],
    origin_x: int,
    origin_y: int,
    win_w: int,
    win_h: int,
) -> Optional[Image.Image]:
    from tools.image_utils import load_image_from_screenshot
    from tools.screenshot import capture_screenshot

    region = {"x": origin_x, "y": origin_y, "w": max(1, win_w), "h": max(1, win_h)}
    shot = capture_screenshot(region=region, window_title=window_title or None)
    if not shot.get("image"):
        return None
    return load_image_from_screenshot(shot)


def _text_from_words_in_elem(
    words: list[dict[str, Any]],
    elem: dict[str, Any],
    origin_x: int,
    origin_y: int,
) -> str:
    ex = int(elem.get("x") or 0) - origin_x
    ey = int(elem.get("y") or 0) - origin_y
    ew = int(elem.get("width") or 0)
    eh = int(elem.get("height") or 0)
    if ew <= 0 or eh <= 0:
        return ""
    hits: list[tuple[int, int, str]] = []
    for word in words:
        wx = int(word.get("x") or 0)
        wy = int(word.get("y") or 0)
        ww = int(word.get("width") or 0)
        wh = int(word.get("height") or 0)
        cx, cy = wx + ww // 2, wy + wh // 2
        if ex <= cx <= ex + ew and ey <= cy <= ey + eh:
            text = (word.get("text") or "").strip()
            if text:
                hits.append((wy, wx, text))
    if not hits:
        return ""
    hits.sort()
    return " ".join(t[2] for t in hits)[:80]


def _roi_ocr_elem(
    window_img: Image.Image,
    elem: dict[str, Any],
    origin_x: int,
    origin_y: int,
    upscale: int = 3,
) -> str:
    ex = int(elem.get("x") or 0) - origin_x
    ey = int(elem.get("y") or 0) - origin_y
    ew = int(elem.get("width") or 0)
    eh = int(elem.get("height") or 0)
    if ew < 4 or eh < 4:
        return ""
    pad = 2
    x0 = max(0, ex - pad)
    y0 = max(0, ey - pad)
    x1 = min(window_img.width, ex + ew + pad)
    y1 = min(window_img.height, ey + eh + pad)
    if x1 - x0 < 4 or y1 - y0 < 4:
        return ""
    crop = window_img.crop((x0, y0, x1, y1))
    words = _ocr_pil_image(crop, upscale=upscale)
    if not words:
        return ""
    return " ".join((w.get("text") or "").strip() for w in words if w.get("text")).strip()[:80]


def enrich_elements_with_ocr(
    elements: list[dict[str, Any]],
    origin_x: int,
    origin_y: int,
    win_w: int,
    win_h: int,
    window_title: Optional[str] = None,
    window_img: Optional[Image.Image] = None,
    roi_fallback: bool = True,
    max_rois: int = 40,
) -> tuple[list[dict[str, Any]], int, int]:
    """Return (elements, window_word_count, enriched_count)."""
    targets = [e for e in elements if _needs_ocr_enrich(e)]
    if not targets:
        return elements, 0, 0

    img = window_img
    if img is None:
        img = capture_window_image(window_title, origin_x, origin_y, win_w, win_h)
    if img is None:
        return elements, 0, 0

    words = _ocr_pil_image(img, upscale=2)
    roi_used = 0
    enriched = 0
    out: list[dict[str, Any]] = []

    for elem in elements:
        row = dict(elem)
        if not _needs_ocr_enrich(row):
            out.append(row)
            continue
        text = _text_from_words_in_elem(words, row, origin_x, origin_y)
        if not text and roi_fallback and roi_used < max_rois and img is not None:
            text = _roi_ocr_elem(img, row, origin_x, origin_y)
            if text:
                roi_used += 1
        if text:
            row["name"] = text
            row["ocr_enriched"] = True
            enriched += 1
        out.append(row)

    return out, len(words), enriched

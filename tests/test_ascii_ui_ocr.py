"""Tests for ASCII UI OCR enrichment."""
from __future__ import annotations

from unittest.mock import patch

from PIL import Image


def test_text_from_words_in_element_bbox():
    from detection.ascii_ui_ocr import _text_from_words_in_elem

    elem = {"x": 100, "y": 100, "width": 60, "height": 40}
    words = [
        {"text": "Hello", "x": 5, "y": 10, "width": 30, "height": 12},
        {"text": "Outside", "x": 200, "y": 200, "width": 20, "height": 10},
    ]
    assert _text_from_words_in_elem(words, elem, 100, 100) == "Hello"


def test_enrich_elements_with_window_ocr_words():
    from detection.ascii_ui_ocr import enrich_elements_with_ocr

    img = Image.new("RGB", (300, 200), "white")
    elements = [
        {
            "role": "Custom",
            "name": "",
            "automation_id": "glyph1",
            "x": 120,
            "y": 80,
            "width": 50,
            "height": 30,
        }
    ]
    words = [{"text": "7", "x": 25, "y": 15, "width": 12, "height": 14}]

    with patch("detection.ascii_ui_ocr._ocr_pil_image", return_value=words):
        out, word_count, enriched = enrich_elements_with_ocr(
            elements,
            100,
            65,
            200,
            150,
            window_img=img,
            roi_fallback=False,
        )
    assert word_count == 1
    assert enriched == 1
    assert out[0]["name"] == "7"
    assert out[0].get("ocr_enriched") is True


def test_enrich_skips_named_elements():
    from detection.ascii_ui_ocr import enrich_elements_with_ocr

    img = Image.new("RGB", (100, 100), "white")
    elements = [{"role": "Button", "name": "OK", "x": 0, "y": 0, "width": 40, "height": 30}]
    with patch("detection.ascii_ui_ocr._ocr_pil_image", return_value=[{"text": "X", "x": 1, "y": 1, "width": 5, "height": 5}]):
        out, _, enriched = enrich_elements_with_ocr(
            elements, 0, 0, 100, 100, window_img=img, roi_fallback=False
        )
    assert enriched == 0
    assert out[0]["name"] == "OK"

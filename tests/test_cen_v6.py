"""Tests for CEN v0.6 features."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "addins", "cen"))

from detect.forms_catalog import catalog_stats, get_popup_hints
from detect.messages import classify_message
from toolbar import resolve_toolbar_intent


class TestMessages:
    def test_classify_validation(self):
        r = classify_message("El campo es mandatorio")
        assert r["success"]
        assert r["category"] in ("validation", "unknown")

    def test_messages_catalog_exists(self):
        path = os.path.join(os.path.dirname(__file__), "..", "addins", "cen", "knowledge", "messages_catalog.json")
        data = json.loads(open(path, encoding="utf-8").read())
        assert data["unique_count"] > 100


class TestCatalogV6:
    def test_catalog_stats(self):
        r = catalog_stats()
        assert r["success"]
        assert r["total_forms"] >= 1000

    def test_index_file(self):
        path = os.path.join(os.path.dirname(__file__), "..", "addins", "cen", "knowledge", "forms_catalog_index.json")
        data = json.loads(open(path, encoding="utf-8").read())
        assert data["total"] >= 1000
        assert "TAD" in (data.get("by_product") or {})

    def test_enriched_form_has_bb_or_uc(self):
        path = os.path.join(os.path.dirname(__file__), "..", "addins", "cen", "knowledge", "forms_catalog.json")
        forms = json.loads(open(path, encoding="utf-8").read())["forms"]
        with_bb = [f for f in forms if f.get("bb_buttons")]
        with_uc = [f for f in forms if f.get("user_controls")]
        assert len(with_bb) > 10 or len(with_uc) > 10


class TestToolbarIntent:
    def test_resolve_from_catalog(self):
        r = resolve_toolbar_intent("search", form_id="FUSUAROL")
        assert r["success"]
        assert "buscar" in (r.get("caption") or "").lower()

"""Tests for CEN forms catalog extraction and query."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "addins", "cen"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from detect.forms_catalog import get_form_profile, list_forms, search_forms
from extract_cen_forms_index import _parse_toolbar, _normalize_form_id


class TestExtractorParsing:
    def test_parse_cmdboton_text(self):
        text = """
        this._cmdBoton_0.Text = "&Buscar";
        this._cmdBoton_1.Text = "Sig&tes.";
        this._cmdBoton_0.Tag = "19004";
        """
        tb = _parse_toolbar(text)
        assert tb["0"]["text"] == "&Buscar"
        assert tb["0"]["tag"] == "19004"
        assert "1" in tb

    def test_normalize_class(self):
        assert _normalize_form_id("FTRANSACCIONClass") == "FTRANSACCION"


class TestFormsCatalog:
    def test_catalog_loaded(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "addins", "cen", "knowledge", "forms_catalog.json"
        )
        data = json.loads(open(path, encoding="utf-8").read())
        assert data.get("total", 0) >= 1000

    def test_list_forms_ftran(self):
        r = list_forms(prefix="FTRAN", limit=10)
        assert r["success"]
        assert r["total"] > 50
        assert all(f["id"].lower().startswith("ftran") for f in r["forms"])

    def test_get_fusuarol(self):
        r = get_form_profile("FUSUAROL")
        assert r["success"]
        assert r["form"]["id"] == "FUSUAROL"
        assert r["form"].get("toolbar")

    def test_search_forms(self):
        r = search_forms("FROLES", limit=5)
        assert r["success"]
        assert any(x["id"] == "FROLES" for x in r["results"])

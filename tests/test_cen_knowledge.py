"""Extended CEN addin tests."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "addins", "cen"))

from detect.classifier import classify_element, classify_elements
from flows import get_flow_hint, list_flows


class TestCenClassifier:
    def test_valid_text(self):
        r = classify_element({"class_name": "COBISValidTextBox", "name": "txtmoneda"})
        assert r["cen_type"] == "cobis_valid_text"
        assert "cen_set_field" in r["mcp_tools"]

    def test_masked_inbox(self):
        r = classify_element({"class_name": "COBISMaskedInBox", "name": "mskFecha_0"})
        assert r["cen_type"] == "cobis_masked_inbox"

    def test_outline(self):
        r = classify_element({"class_name": "COBISMSOutline", "name": "otlOficiales"})
        assert r["cen_type"] == "cobis_outline"

    def test_toolbar(self):
        r = classify_element({"name": "_cmdBoton_0", "class_name": "ToolStripButton"})
        assert r["cen_type"] == "toolbar_cmdboton"

    def test_batch_classify(self):
        elems = [
            {"name": "grdRegistros", "class_name": "COBISGrid"},
            {"name": "txtconvenio", "class_name": "COBISValidTextBox"},
        ]
        out = classify_elements(elems)
        assert out[0]["cen"]["cen_type"] == "cobis_grid"
        assert out[1]["cen"]["cen_type"] == "cobis_valid_text"


class TestCenFlows:
    def test_list_flows(self):
        r = list_flows()
        assert r["success"]
        assert len(r["flows"]) >= 7

    def test_get_consulta_flow(self):
        r = get_flow_hint("consulta_estandar")
        assert r["success"]
        assert "Buscar" in str(r.get("toolbar_captions", []))

    def test_unknown_flow(self):
        r = get_flow_hint("nonexistent")
        assert not r["success"]
        assert "available" in r


class TestCenKnowledge:
    def test_controls_json_loads(self):
        path = os.path.join(os.path.dirname(__file__), "..", "addins", "cen", "knowledge", "controls.json")
        data = json.loads(open(path, encoding="utf-8").read())
        ids = {c["id"] for c in data["controls"]}
        assert "cobis_grid" in ids
        assert "cobis_spread" in ids
        assert "cobis_valid_text" in ids

    def test_modules_json_products(self):
        path = os.path.join(os.path.dirname(__file__), "..", "addins", "cen", "knowledge", "modules.json")
        data = json.loads(open(path, encoding="utf-8").read())
        codes = {p["code"] for p in data["products"]}
        assert "TAD" in codes
        assert "ADM" in codes

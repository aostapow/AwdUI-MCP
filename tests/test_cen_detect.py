"""Tests for CEN modal/form detection and agent helpers."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "addins", "cen"))

from detect.forms import match_form_profile
from detect.modals import detect_modal


class TestCenModals:
    def test_detect_grid_valores(self):
        elements = [
            {"name": "gr_SQL", "class_name": "COBISGrid"},
            {"name": "bb_buscar", "automation_id": "bb_buscar"},
            {"name": "bb_escoger", "automation_id": "bb_escoger"},
        ]
        r = detect_modal("Listado de Registros", elements)
        assert r["modal_open"]
        assert r["modal_type"] == "grid_valores"

    def test_detect_buscar_cliente(self):
        elements = [
            {"name": "GrdResultados", "class_name": "COBISGrid"},
            {"name": "cmdBuscar"},
            {"name": "FBUSCLI"},
        ]
        r = detect_modal("Buscar Cliente", elements)
        assert r["modal_open"]
        assert r["modal_type"] == "buscar_cliente"

    def test_no_modal(self):
        elements = [{"name": "txtconvenio"}, {"name": "grdRegistros"}]
        r = detect_modal("Consulta", elements)
        assert not r["modal_open"]


class TestCenFormProfiles:
    def test_match_ftransac(self):
        elements = [
            {"name": "txtconvenio"},
            {"name": "txtmoneda"},
            {"name": "grdRegistros"},
        ]
        r = match_form_profile("FTRANSAC consulta", elements)
        assert r["matched"]
        assert r["form_id"] == "FTRANSAC"
        assert "0" in r["toolbar_map"]

    def test_match_fusuarol(self):
        elements = [{"name": "txtCampo_0"}, {"name": "grdValores"}]
        r = match_form_profile("Usuario Rol", elements)
        assert r["matched"]
        assert r["form_id"] == "FUSUAROL"


class TestCenKnowledgeExtended:
    def test_modals_json(self):
        path = os.path.join(os.path.dirname(__file__), "..", "addins", "cen", "knowledge", "modals.json")
        data = json.loads(open(path, encoding="utf-8").read())
        ids = {m["id"] for m in data["modals"]}
        assert "grid_valores" in ids
        assert "buscar_cliente" in ids

    def test_forms_index(self):
        path = os.path.join(os.path.dirname(__file__), "..", "addins", "cen", "knowledge", "forms_index.json")
        data = json.loads(open(path, encoding="utf-8").read())
        ids = {f["id"] for f in data["forms"]}
        assert "FTRANSAC" in ids
        assert "FTRAN024" in ids

    def test_classifier_tristate_tree(self):
        from detect.classifier import classify_element

        r = classify_element({"class_name": "TriStateTreeView", "name": "trvPermisos"})
        assert r["cen_type"] == "cobis_tristate_tree"

    def test_classifier_picvisto(self):
        from detect.classifier import classify_element

        r = classify_element({"class_name": "PictureBox", "name": "picVisto"})
        assert r["cen_type"] == "cobis_grid_checkbox"

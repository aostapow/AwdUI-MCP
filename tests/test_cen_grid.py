"""Unit tests for COBIS CEN grid helpers (no live COBIS required)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "addins", "cen"))

from grid.detect import detect_grid_type
from grid.farpoint_cells import _parse_cell


class TestCenGridDetect:
    def test_detect_cobis_spread(self):
        out = detect_grid_type(
            {"class_name": "COBISSpread", "name": "grdRegistros", "role": "Pane"},
            ["grdRegistros, Sheet1, Row 1, Column 2, value"],
        )
        assert out["grid_type"] == "cobis_spread"

    def test_detect_cobis_grid_by_name(self):
        out = detect_grid_type({"class_name": "Panel", "name": "grdTotales", "role": "Pane"})
        assert out["grid_type"] == "cobis_grid"

    def test_detect_uia_table(self):
        out = detect_grid_type({"class_name": "X", "name": "grid", "role": "DataGrid"})
        assert out["grid_type"] == "uia_table"


class TestFarpointParse:
    def test_parse_row_column(self):
        assert _parse_cell("", "grd, Sheet1, Row 2, Column 3, ABC") == (2, 3, "grd, Sheet1, Row 2, Column 3, ABC")

    def test_parse_devexpress_row(self):
        assert _parse_cell("Amount row 4", "") == (4, 0, "Amount row 4")

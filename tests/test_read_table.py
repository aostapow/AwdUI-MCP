"""Tests for read_table (full grid as headers + rows)."""
from __future__ import annotations

from detection.table_read import (
    public_table_payload,
    read_table_devexpress,
    read_table_pattern,
)


class _FakePattern:
    def __init__(self, rows, cols, values):
        self.CurrentRowCount = rows
        self.CurrentColumnCount = cols
        self._values = values
        self.calls = []

    def GetItem(self, row, col):
        self.calls.append((row, col))
        return self._values.get((row, col))


def test_read_table_devexpress(monkeypatch):
    rows = [
        {
            "row_index": 0,
            "name": "108082-1-1: BM-MANT",
            "cells": {"titulo": "108082-1-1: BM-MANT", "actividad id": "108082"},
        },
        {
            "row_index": 1,
            "name": "OTRO",
            "cells": {"titulo": "OTRO", "actividad id": "999"},
        },
    ]
    monkeypatch.setattr("detection.table_read.group_grid_rows", lambda _r: rows)

    payload = read_table_devexpress(object(), filter_text="108082", limit=10)
    assert payload is not None
    assert payload["headers"] == ["actividad id", "titulo"]
    assert payload["rows"] == [["108082", "108082-1-1: BM-MANT"]]
    assert payload["total_rows"] == 1
    assert payload["source"] == "grid_rows"


def test_read_table_pattern(monkeypatch):
    pattern = _FakePattern(
        rows=2,
        cols=2,
        values={
            (0, 0): "A1",
            (0, 1): "B1",
            (1, 0): "A2",
            (1, 1): "B2",
        },
    )

    class _Raw:
        element_info = type("EI", (), {"element": object()})()

    monkeypatch.setattr(
        "pywinauto.uia_defines.get_elem_interface",
        lambda _el, name: pattern,
    )
    monkeypatch.setattr("detection.table_read._collect_header_items", lambda _r: [])
    monkeypatch.setattr(
        "detection.table_read._cell_value_from_raw",
        lambda raw: str(raw),
    )

    payload = read_table_pattern(_Raw(), offset=0, limit=10)
    assert payload is not None
    assert payload["headers"] == ["column_0", "column_1"]
    assert payload["rows"] == [["A1", "B1"], ["A2", "B2"]]
    assert payload["source"] == "uia_grid"


def test_public_table_payload():
    payload = public_table_payload(
        {
            "headers": ["a"],
            "rows": [["1"]],
            "row_count": 1,
            "total_rows": 1,
            "offset": 0,
            "limit": 200,
            "has_more": False,
            "source": "grid_rows",
            "internal": "strip",
        }
    )
    assert payload == {
        "headers": ["a"],
        "rows": [["1"]],
        "row_count": 1,
        "total_rows": 1,
        "offset": 0,
        "limit": 200,
        "has_more": False,
        "source": "grid_rows",
    }


def test_do_read_table(monkeypatch):
    from tools.control_items import do_read_table

    class _Elem:
        role = "Table"
        name = "grid"

    monkeypatch.setattr(
        "tools.control_items._resolve_control",
        lambda aid, wt: (object(), _Elem(), {}, {"resolved_title": "AST"}),
    )
    monkeypatch.setattr(
        "detection.table_read.read_table",
        lambda *a, **k: {
            "headers": ["titulo"],
            "rows": [["A"]],
            "row_count": 1,
            "total_rows": 1,
            "offset": 0,
            "limit": 200,
            "has_more": False,
            "source": "grid_rows",
        },
    )

    out = do_read_table("gcGrillaActividades", filter_text="A")
    assert out["success"] is True
    assert out["headers"] == ["titulo"]
    assert out["rows"] == [["A"]]


def test_do_read_table_wrong_role(monkeypatch):
    from tools.control_items import do_read_table

    class _Elem:
        role = "Button"

    monkeypatch.setattr(
        "tools.control_items._resolve_control",
        lambda aid, wt: (object(), _Elem(), {}, {}),
    )
    out = do_read_table("btnOk")
    assert out["success"] is False
    assert "not a table" in out["error"]

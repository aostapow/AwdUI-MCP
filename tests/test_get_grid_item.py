"""Tests for get_grid_item (grid cell by row/column)."""
from detection.grid_items import (
    get_grid_item_devexpress,
    public_grid_item,
)


class _FakeRaw:
    pass


def test_get_grid_item_devexpress_by_index(monkeypatch):
    rows = [
        {
            "row_index": 0,
            "name": "108082-1-1: BM-MANT",
            "cells": {"titulo": "108082-1-1: BM-MANT", "actividad id": "108082"},
            "cell_raws": {"titulo": _FakeRaw(), "actividad id": _FakeRaw()},
            "x": 424,
            "y": 208,
            "width": 309,
            "height": 25,
        },
        {
            "row_index": 1,
            "name": "OTRO",
            "cells": {"titulo": "OTRO", "actividad id": "999"},
            "cell_raws": {"titulo": _FakeRaw(), "actividad id": _FakeRaw()},
            "x": 424,
            "y": 234,
            "width": 309,
            "height": 25,
        },
    ]
    monkeypatch.setattr("detection.grid_items.group_grid_rows", lambda _r: rows)

    cell = get_grid_item_devexpress(object(), row_index=0, column_index=0)
    assert cell is not None
    assert cell["value"] == "108082"
    assert cell["column_name"] == "actividad id"
    assert cell["source"] == "grid_rows"

    by_name = get_grid_item_devexpress(object(), row_index=1, column_name="titulo")
    assert by_name["value"] == "OTRO"


def test_public_grid_item_strips_raw():
    payload = public_grid_item({"value": "x", "item_raw": object(), "row": {}})
    assert payload == {"value": "x"}


def test_do_get_grid_item(monkeypatch):
    from tools.control_items import do_get_grid_item

    class _Elem:
        role = "Table"
        name = "grid"

    monkeypatch.setattr(
        "tools.control_items._resolve_control",
        lambda aid, wt: (object(), _Elem(), {}, {"resolved_title": "AST"}),
    )
    monkeypatch.setattr(
        "detection.grid_items.get_grid_item",
        lambda *a, **k: {
            "row_index": 0,
            "column_index": 0,
            "column_name": "titulo",
            "value": "A",
            "name": "A",
            "x": 1,
            "y": 2,
            "width": 3,
            "height": 4,
            "source": "grid_rows",
            "item_raw": None,
        },
    )

    out = do_get_grid_item("gcGrillaActividades", row=0, column=0)
    assert out["success"] is True
    assert out["value"] == "A"
    assert out["automation_id"] == "gcGrillaActividades"


def test_do_get_grid_item_wrong_role(monkeypatch):
    from tools.control_items import do_get_grid_item

    class _Elem:
        role = "Button"
        name = "btn"

    monkeypatch.setattr(
        "tools.control_items._resolve_control",
        lambda aid, wt: (object(), _Elem(), {}, {}),
    )
    out = do_get_grid_item("btnOk", row=0, column=0)
    assert out["success"] is False
    assert "not a grid" in out["error"]

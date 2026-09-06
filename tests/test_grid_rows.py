"""Tests for DevExpress-style grid row assembly."""
from detection.grid_rows import (
    collect_grid_rows,
    find_grid_row,
    group_grid_rows,
    parse_row_cell_name,
    row_matches,
)


class _FakeRaw:
    pass


def test_parse_row_cell_name():
    assert parse_row_cell_name("titulo row 0") == ("titulo", 0)
    assert parse_row_cell_name("actividad ID row 3") == ("actividad id", 3)
    assert parse_row_cell_name("Button") is None


def test_group_grid_rows(monkeypatch):
    cells = [
        ("titulo row 0", "108082-1-1: BM-MANT", 424, 208, 309, 25),
        ("actividad ID row 0", "108082", 734, 208, 311, 25),
        ("titulo row 1", "OTRO", 424, 234, 309, 25),
    ]

    class _Info:
        def __init__(self, name, x, y, w, h):
            self.name = name
            self.control_type = "DataItem"
            self.rectangle = type("R", (), {
                "left": x, "top": y, "right": x + w, "bottom": y + h,
            })()
            self.element = _FakeRaw()
            self.automation_id = ""
            self.class_name = ""
            self.framework_id = "WinForm"
            self.process_id = 1
            self.handle = 0
            self.visible = True
            self.runtime_id = []

    class _Wrap:
        def __init__(self, name, x, y, w, h):
            self.element_info = _Info(name, x, y, w, h)

    raw_by_name = {}

    def fake_walk(_root, max_nodes=8000):
        for name, *_rest in cells:
            yield raw_by_name[name]

    def fake_wrap(raw):
        for name, text, x, y, w, h in cells:
            if raw_by_name.get(name) is raw:
                return _Wrap(name, x, y, w, h)
        return None

    def fake_cell_text(raw):
        for name, text, *_rest in cells:
            if raw_by_name.get(name) is raw:
                return text
        return ""

    for name, *_rest in cells:
        raw_by_name[name] = _FakeRaw()

    monkeypatch.setattr("detection.grid_rows._walk_control_tree", fake_walk)
    monkeypatch.setattr("detection.grid_rows._wrap_raw", fake_wrap)
    monkeypatch.setattr("detection.grid_rows.get_cell_text", fake_cell_text)
    monkeypatch.setattr(
        "detection.backends.uia_backend._pywinauto_to_element",
        lambda w: type("D", (), {
            "name": w.element_info.name,
            "role": "DataItem",
            "x": w.element_info.rectangle.left,
            "y": w.element_info.rectangle.top,
            "width": w.element_info.rectangle.right - w.element_info.rectangle.left,
            "height": w.element_info.rectangle.bottom - w.element_info.rectangle.top,
            "automation_id": "",
            "to_dict": lambda self=None: {},
        })(),
    )

    rows = group_grid_rows(object())
    assert len(rows) == 2
    assert "108082" in rows[0]["name"]
    assert row_matches(rows[0], "108082")
    assert not row_matches(rows[1], "108082")

    batch = collect_grid_rows(object(), filter_text="108082", limit=10)
    assert batch["matched_total"] == 1
    assert batch["items"][0]["row_index"] == 0

    found = find_grid_row(object(), "108082", column="actividad id")
    assert found is not None
    assert found[1]["cells"]["actividad id"] == "108082"


def test_select_grid_row_by_index(monkeypatch):
    rows = [
        {"row_index": 0, "name": "A", "cells": {"titulo": "A"}, "cell_raws": {"titulo": _FakeRaw()}},
        {"row_index": 1, "name": "B", "cells": {"titulo": "B"}, "cell_raws": {"titulo": _FakeRaw()}},
    ]
    from detection.grid_rows import select_grid_row_by_index
    monkeypatch.setattr("detection.grid_rows.group_grid_rows", lambda _r: rows)
    picked = select_grid_row_by_index(object(), 1, column="titulo")
    assert picked is not None
    assert picked[1]["name"] == "B"

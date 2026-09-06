"""Tests for UIA item name matching helpers."""
from detection.uia_find import _matches_filter, find_item_raw_by_name


class _FakeRoot:
    pass


def test_matches_filter_accent_insensitive():
    assert _matches_filter({"name": "Estándar"}, "Estandar")
    assert _matches_filter({"name": "Seis"}, "seis")


def test_find_item_raw_by_name_walks_buttons(monkeypatch):
    item = {
        "name": "Estándar",
        "value": "",
        "display_text": "",
        "item_raw": object(),
    }

    monkeypatch.setattr("detection.uia_find._list_item_nodes", lambda _root: [item])
    raw, found = find_item_raw_by_name(_FakeRoot(), "Estandar")
    assert raw is item["item_raw"]
    assert found["name"] == "Estándar"

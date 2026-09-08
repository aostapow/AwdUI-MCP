"""Tests for contenteditable read cascade."""
from detection.uia_text import is_placeholder_text, read_editable_text


def test_is_placeholder_detects_teams_hint():
    assert is_placeholder_text("Escribe un mensaje")
    assert not is_placeholder_text("Hola equipo")


def test_read_editable_prefers_value_pattern():
    props = {
        "role": "Document",
        "patterns": {"Value": {"value": "Mensaje real"}},
        "name": "Escribe un mensaje",
    }
    out = read_editable_text(props, allow_clipboard=False)
    assert out["success"] is True
    assert out["text"] == "Mensaje real"
    assert out["read_method"] == "ValuePattern"


def test_read_editable_skips_placeholder_name():
    props = {
        "role": "Document",
        "name": "Escribe un mensaje",
        "value": "",
    }
    out = read_editable_text(props, allow_clipboard=False)
    assert out.get("placeholder") is True
    assert out["success"] is False

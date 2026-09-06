"""Tests for paginated control item collection."""
from detection.uia_find import collect_control_items


class _FakeItem:
    def __init__(self, name, role="ListItem", x=0, y=0, w=10, h=10):
        self.name = name
        self.role = role
        self.x = x
        self.y = y
        self.width = w
        self.height = h
        self.automation_id = ""
        self.value = ""

    def to_dict(self):
        return {
            "name": self.name,
            "role": self.role,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "automation_id": self.automation_id,
        }


def test_collect_pagination(monkeypatch):
    items = [_FakeItem(f"Item {i}") for i in range(25)]

    def fake_list(_root):
        return [it.to_dict() for it in items]

    monkeypatch.setattr("detection.uia_find._list_item_nodes", lambda _r: fake_list(_r))

    page0 = collect_control_items(object(), offset=0, limit=10)
    assert page0["returned"] == 10
    assert page0["has_more"] is True
    assert page0["matched_total"] == 25

    page2 = collect_control_items(object(), offset=20, limit=10)
    assert page2["returned"] == 5
    assert page2["has_more"] is False


def test_collect_filter(monkeypatch):
    items = [
        _FakeItem("ACCUSYS HOMOLOGACION"),
        _FakeItem("OTRO GRUPO"),
        _FakeItem("ACCUSYS TF"),
    ]

    monkeypatch.setattr(
        "detection.uia_find._list_item_nodes",
        lambda _r: [it.to_dict() for it in items],
    )

    result = collect_control_items(object(), filter_text="homologacion", offset=0, limit=10)
    assert result["matched_total"] == 1
    assert result["items"][0]["name"] == "ACCUSYS HOMOLOGACION"


def test_select_control_item_double_click(monkeypatch):
    from tools import control_items

    fake_item = {
        "name": "108082 - BM - MANT",
        "x": 100,
        "y": 200,
        "width": 400,
        "height": 20,
    }
    clicks = []

    class _Elem:
        role = "Table"
        name = "grid"
        value = ""

    class _Info:
        element = object()

    class _Raw:
        element_info = _Info()

    monkeypatch.setattr(
        control_items,
        "_resolve_control",
        lambda _aid, _wt: (_Raw(), _Elem(), None, None),
    )
    monkeypatch.setattr(
        "detection.uia_find.find_item_raw_by_name",
        lambda _r, _v: (object(), fake_item),
    )
    monkeypatch.setattr(
        control_items,
        "_try_selection_item",
        lambda raw, dc, x, y: None,
    )
    monkeypatch.setattr(
        "tools.input_tools.do_double_click",
        lambda x, y: clicks.append((x, y)) or {"action": "click", "clicks": 2},
    )
    monkeypatch.setattr(
        "tools.window_scope.resolve_window_scope",
        lambda _t: {"resolved_title": "Buscar"},
    )

    result = control_items.do_select_control_item(
        "gcGrid",
        "108082",
        window_title="Buscar",
        double_click=True,
    )
    assert result["success"] is True
    assert result["method"] == "double_click"
    assert clicks == [(300, 210)]


def test_combo_select_verifies_value_no_set_value_fallback(monkeypatch):
    """ComboBox must use popup list + verify read-back; never set_value."""
    from tools import control_items

    class _Elem:
        role = "ComboBox"
        name = "cboGrupo"
        value = ""

    class _Info:
        element = object()

    class _Raw:
        element_info = _Info()

    monkeypatch.setattr(
        control_items,
        "_resolve_control",
        lambda _aid, _wt: (_Raw(), _Elem(), None, None),
    )
    monkeypatch.setattr(control_items, "_expand_combo", lambda _r: None)
    monkeypatch.setattr(
        "detection.uia_find.collect_control_items",
        lambda *a, **k: {"items": [], "has_more": False},
    )
    monkeypatch.setattr(
        control_items,
        "_select_combo_descendants",
        lambda raw, val: None,
    )
    monkeypatch.setattr(
        "detection.winforms_combo.find_combo_item",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "tools.window_scope.resolve_window_scope",
        lambda _t: {"resolved_title": "AST"},
    )
    set_value_calls = []
    monkeypatch.setattr(
        "tools.ui_automation.do_set_element_value",
        lambda *a, **k: set_value_calls.append(1) or {"success": True},
    )

    result = control_items.do_select_control_item(
        "cboGrupo",
        "homologacion",
        window_title="AST",
    )
    assert result["success"] is False
    assert "not found" in result["error"].lower()
    assert set_value_calls == []


def test_combo_select_success_returns_verified_value(monkeypatch):
    from tools import control_items

    class _Elem:
        role = "ComboBox"
        name = "cboGrupo"
        value = ""

    class _Info:
        element = object()

    class _Raw:
        element_info = _Info()

    item = {"name": "ACCUSYS HOMOLOGACION", "x": 10, "y": 20, "width": 100, "height": 20}

    monkeypatch.setattr(
        control_items,
        "_resolve_control",
        lambda _aid, _wt: (_Raw(), _Elem(), None, None),
    )
    monkeypatch.setattr(control_items, "_expand_combo", lambda _r: None)
    monkeypatch.setattr(
        "detection.uia_find.collect_control_items",
        lambda *a, **k: {"items": [item], "has_more": False},
    )
    monkeypatch.setattr(
        "detection.uia_find.find_item_raw_by_name",
        lambda _r, _n: (object(), item),
    )
    monkeypatch.setattr(
        control_items,
        "_activate_item",
        lambda **k: {"success": True, "method": "click_item", "selected": item["name"]},
    )
    monkeypatch.setattr(
        control_items,
        "_read_control_value",
        lambda _r: "ACCUSYS HOMOLOGACION",
    )
    monkeypatch.setattr(
        "tools.window_scope.resolve_window_scope",
        lambda _t: {"resolved_title": "AST"},
    )

    result = control_items.do_select_control_item(
        "cboGrupo",
        "homologacion",
        window_title="AST",
    )
    assert result["success"] is True
    assert result.get("verified_value") == "ACCUSYS HOMOLOGACION"
    assert "set_value" not in result.get("method", "")


def test_combo_select_descendants_fallback(monkeypatch):
    from tools import control_items

    class _Elem:
        role = "ComboBox"
        name = "cboGrupo"
        value = ""

    class _Info:
        element = object()

    class _Raw:
        element_info = _Info()

        def descendants(self):
            return []

    monkeypatch.setattr(
        control_items,
        "_resolve_control",
        lambda _aid, _wt: (_Raw(), _Elem(), None, None),
    )
    monkeypatch.setattr(control_items, "_expand_combo", lambda _r: None)
    monkeypatch.setattr(
        "detection.uia_find.collect_control_items",
        lambda *a, **k: {"items": [], "has_more": False},
    )
    monkeypatch.setattr(
        control_items,
        "_select_combo_descendants",
        lambda raw, val: {
            "success": True,
            "method": "SelectionItem",
            "selected": "ACCUSYS HOMOLOGACION",
            "verified_value": "ACCUSYS HOMOLOGACION",
        },
    )
    monkeypatch.setattr(
        "tools.window_scope.resolve_window_scope",
        lambda _t: {"resolved_title": "AST"},
    )

    result = control_items.do_select_control_item(
        "cboGrupo",
        "homologacion",
        window_title="AST",
    )
    assert result["success"] is True
    assert result.get("verified_value") == "ACCUSYS HOMOLOGACION"


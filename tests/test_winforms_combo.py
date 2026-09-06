"""Tests for WinForms combo item enumeration (Strategy D)."""
import ctypes
from ctypes import wintypes

from detection.winforms_combo import (
    _enumerate_uia_items,
    _is_plausible_item,
    _win32_list_items,
    click_target_for_item,
    collect_combo_items,
    combolbox_item_screen_rect,
    find_combo_item,
    is_placeholder_item,
    item_requires_click_operation,
)


class _FakeRaw:
    pass


def test_is_plausible_item():
    assert _is_plausible_item("ACCUSYS HOMOLOGACION", "homologacion")
    assert not _is_plausible_item("Grupo:", "")
    assert not _is_plausible_item("x", "")
    assert not _is_plausible_item("OTRO", "homologacion")


def test_enumerate_uia_items_reads_legacy_text(monkeypatch):
    nodes = [
        ("ListItem", "ACCUSYS HOMOLOGACION", 10, 20, 100, 18),
        ("ListItem", "", 0, 0, 0, 0),
        ("Text", "Grupo:", 0, 0, 50, 18),
    ]
    raw_map = {}

    class _Info:
        def __init__(self, role, name, x, y, w, h):
            self.name = name
            self.control_type = role
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
        def __init__(self, role, name, x, y, w, h):
            self.element_info = _Info(role, name, x, y, w, h)

    texts = {}

    def fake_walk(_root, max_nodes=8000):
        for key in raw_map:
            yield raw_map[key]

    def fake_wrap(raw):
        for role, name, x, y, w, h in nodes:
            if raw_map.get((role, name)) is raw:
                return _Wrap(role, name, x, y, w, h)
        return None

    def fake_cell_text(raw):
        return texts.get(id(raw), "")

    for role, name, x, y, w, h in nodes:
        r = _FakeRaw()
        raw_map[(role, name)] = r
        texts[id(r)] = name

    monkeypatch.setattr("detection.winforms_combo._walk_control_tree", fake_walk)
    monkeypatch.setattr("detection.winforms_combo._wrap_raw", fake_wrap)
    monkeypatch.setattr("detection.winforms_combo.get_item_text", fake_cell_text)
    monkeypatch.setattr(
        "detection.backends.uia_backend._pywinauto_to_element",
        lambda w: type("D", (), {
            "name": w.element_info.name,
            "role": w.element_info.control_type,
            "x": w.element_info.rectangle.left,
            "y": w.element_info.rectangle.top,
            "width": w.element_info.rectangle.right - w.element_info.rectangle.left,
            "height": w.element_info.rectangle.bottom - w.element_info.rectangle.top,
            "automation_id": "",
        })(),
    )

    items = _enumerate_uia_items(_FakeRaw(), filter_text="homologacion")
    assert len(items) == 1
    assert items[0]["name"] == "ACCUSYS HOMOLOGACION"


def test_collect_combo_items_merges_win32(monkeypatch):
    monkeypatch.setattr(
        "detection.winforms_combo._enumerate_uia_items",
        lambda *a, **k: [],
    )
    monkeypatch.setattr(
        "detection.winforms_combo._combo_popup_roots",
        lambda *a, **k: [],
    )
    monkeypatch.setattr("detection.winforms_combo._native_handle", lambda _r: 12345)
    monkeypatch.setattr(
        "detection.winforms_combo._win32_list_items",
        lambda hwnd, filter_text="": [
            {
                "name": "Horas Calendario",
                "role": "ListItem",
                "x": 0, "y": 0, "width": 1, "height": 1,
                "automation_id": "",
                "item_raw": None,
                "win32_index": 0,
                "win32_hwnd": 999,
            }
        ],
    )
    monkeypatch.setattr("detection.winforms_combo.apply_filter_to_combo", lambda *a, **k: None)
    monkeypatch.setattr("detection.winforms_combo.expand_combo", lambda *a, **k: None)

    result = collect_combo_items(
        _FakeRaw(),
        filter_text="calendario",
        combo_wrapper=object(),
    )
    assert result["source"] == "winforms_combo"
    assert result["matched_total"] == 1
    assert result["items"][0]["name"] == "Horas Calendario"


def test_find_combo_item(monkeypatch):
    item = {
        "name": "ACCUSYS HOMOLOGACION",
        "role": "ListItem",
        "x": 1, "y": 2, "width": 10, "height": 10,
        "item_raw": _FakeRaw(),
    }
    monkeypatch.setattr(
        "detection.winforms_combo._collect_with_raw",
        lambda *a, **k: [item],
    )
    found = find_combo_item(_FakeRaw(), "homologacion")
    assert found is not None
    raw, it = found
    assert it["name"] == "ACCUSYS HOMOLOGACION"
    assert raw is item["item_raw"]


def test_control_items_list_falls_back_to_winforms_combo(monkeypatch):
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
        lambda *a, **k: {
            "items": [],
            "matched_total": 0,
            "returned": 0,
            "has_more": False,
            "offset": 0,
            "limit": 10,
        },
    )
    monkeypatch.setattr(
        "detection.winforms_combo.collect_combo_items",
        lambda *a, **k: {
            "items": [{"name": "ACCUSYS HOMOLOGACION", "x": 1, "y": 2, "width": 10, "height": 10}],
            "matched_total": 1,
            "returned": 1,
            "has_more": False,
            "offset": 0,
            "limit": 10,
            "source": "winforms_combo",
        },
    )
    monkeypatch.setattr(
        "tools.window_scope.resolve_window_scope",
        lambda _t: {"resolved_title": "AST"},
    )

    result = control_items.do_list_control_items(
        "cboGrupo",
        filter_text="homologacion",
        window_title="AST",
    )
    assert result["success"] is True
    assert result.get("source") == "winforms_combo"
    assert result["matched_total"] == 1


def test_placeholder_and_click_operation_flags():
    placeholder = {"x": 0, "y": 0, "width": 1, "height": 1, "win32_hwnd": 1}
    popup = {
        "x": 100,
        "y": 200,
        "width": 300,
        "height": 22,
        "win32_hwnd": 999,
        "selection_via": "click",
    }
    assert is_placeholder_item(placeholder)
    assert not item_requires_click_operation(placeholder)
    assert item_requires_click_operation(popup)
    target = click_target_for_item(popup)
    assert target == {"x": 250, "y": 211}


def test_combolbox_item_screen_rect_maps_to_screen(monkeypatch):
    user32 = ctypes.windll.user32
    calls = []

    class _RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    def fake_send(hwnd, msg, wparam, lparam):
        calls.append((msg, wparam))
        rect = ctypes.cast(lparam, ctypes.POINTER(_RECT)).contents
        rect.left, rect.top, rect.right, rect.bottom = 0, 0, 120, 18
        return 1

    points = [(10, 200), (130, 218)]

    def fake_client_to_screen(hwnd, pt_ptr):
        pt = ctypes.cast(pt_ptr, ctypes.POINTER(wintypes.POINT)).contents
        pt.x, pt.y = points.pop(0)
        return 1

    monkeypatch.setattr(user32, "SendMessageW", fake_send)
    monkeypatch.setattr(user32, "ClientToScreen", fake_client_to_screen)

    rect = combolbox_item_screen_rect(555, 2)
    assert rect == (10, 200, 120, 18)


def test_select_control_item_returns_click_operation_hint(monkeypatch):
    from tools import control_items

    class _Elem:
        role = "ComboBox"
        name = "cboActividad"
        value = ""

    class _Info:
        element = object()

    class _Raw:
        element_info = _Info()

    popup_item = {
        "name": "108082 - 1 - 1: BM - MANT. SOC",
        "x": 100,
        "y": 220,
        "width": 400,
        "height": 20,
        "win32_hwnd": 999,
        "win32_index": 0,
        "selection_via": "click",
        "item_raw": None,
    }

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
        lambda *a, **k: (None, popup_item),
    )
    monkeypatch.setattr(
        "tools.window_scope.resolve_window_scope",
        lambda _t: {"resolved_title": "AST"},
    )

    result = control_items.do_select_control_item(
        "cboActividad",
        "108082",
        window_title="AST",
    )
    assert result["success"] is False
    assert result["requires_operation"] == "click"
    assert result["click_at"] == {"x": 300, "y": 230}

"""Tests for ASCII UI eye renderer."""
from __future__ import annotations


def _calc_like_elements():
    ox, oy = 100, 100
    return [
        {
            "role": "Text",
            "name": "Display is 0",
            "automation_id": "CalculatorResults",
            "x": ox + 20,
            "y": oy + 20,
            "width": 280,
            "height": 60,
            "is_keyboard_focusable": True,
        },
        {
            "role": "Button",
            "name": "7",
            "automation_id": "num7Button",
            "x": ox + 20,
            "y": oy + 100,
            "width": 60,
            "height": 50,
            "is_keyboard_focusable": True,
        },
        {
            "role": "Button",
            "name": "8",
            "automation_id": "num8Button",
            "x": ox + 90,
            "y": oy + 100,
            "width": 60,
            "height": 50,
            "is_keyboard_focusable": True,
        },
        {
            "role": "Button",
            "name": "9",
            "automation_id": "num9Button",
            "x": ox + 160,
            "y": oy + 100,
            "width": 60,
            "height": 50,
            "is_keyboard_focusable": True,
        },
        {
            "role": "Button",
            "name": "plus",
            "automation_id": "plusButton",
            "x": ox + 240,
            "y": oy + 100,
            "width": 60,
            "height": 50,
            "is_keyboard_focusable": True,
        },
        {
            "role": "Button",
            "name": "Equals",
            "automation_id": "equalButton",
            "x": ox + 240,
            "y": oy + 220,
            "width": 60,
            "height": 50,
            "is_keyboard_focusable": True,
        },
    ]


def test_filter_elements_drops_huge_pane():
    from detection.ascii_ui_render import filter_elements_for_ascii

    elems = [
        {"role": "Pane", "name": "", "automation_id": "", "x": 0, "y": 0, "width": 400, "height": 500},
        {"role": "Button", "name": "OK", "automation_id": "btnOk", "x": 50, "y": 50, "width": 80, "height": 30},
    ]
    out = filter_elements_for_ascii(elems, 0, 0, 400, 500, min_pixels=10)
    assert len(out) == 1
    assert out[0]["automation_id"] == "btnOk"


def test_render_ascii_contains_labels_and_keys():
    from detection.ascii_ui_render import render_ascii_ui, select_elements_for_ascii_render

    elems = _calc_like_elements()
    filtered = select_elements_for_ascii_render(elems, 100, 100, 320, 280, min_pixels=8)
    result = render_ascii_ui(
        filtered, 100, 100, 320, 280, cols=72, height=24, title="Calculadora", unicode_box=True
    )
    ascii_map = result["ascii"]
    assert "┌" in ascii_map or "+" in ascii_map
    assert "Calculadora" in ascii_map
    assert result["rendered_count"] >= 4
    assert len(result["elements"]) >= 4
    aids = {e["automation_id"] for e in result["elements"]}
    assert "num7Button" in aids
    assert result["viewport"]["mode"] == "proportional"
    assert "7" in ascii_map or "num7Button" in ascii_map
    keys = {e["key"] for e in result["elements"]}
    assert "e1" in keys and "e2" in keys
    assert len([e for e in result["elements"] if e.get("tab_index")]) >= 3


def test_render_ascii_plain_box_mode():
    from detection.ascii_ui_render import render_ascii_ui, select_elements_for_ascii_render

    elems = _calc_like_elements()[:2]
    filtered = select_elements_for_ascii_render(elems, 100, 100, 320, 280, min_pixels=8)
    result = render_ascii_ui(filtered, 100, 100, 320, 280, cols=60, height=18, unicode_box=False)
    assert "+" in result["ascii"]
    assert "┌" not in result["ascii"]


def test_role_glyph_checkbox():
    from detection.ascii_ui_render import _role_glyph_row

    on = _role_glyph_row({"role": "CheckBox", "name": "Wrap", "selected": True}, 20)
    assert on and "[x]" in on
    off = _role_glyph_row({"role": "CheckBox", "name": "Wrap", "selected": False}, 20)
    assert off and "[ ]" in off


def test_legible_cell_layout_fills_grid():
    from detection.ascii_ui_render import compute_legible_cell_layout

    elems = [
        {"role": "Button", "name": "A", "automation_id": "a", "x": 10, "y": 10, "width": 40, "height": 40},
        {"role": "Button", "name": "B", "automation_id": "b", "x": 60, "y": 10, "width": 40, "height": 40},
        {"role": "Button", "name": "C", "automation_id": "c", "x": 10, "y": 60, "width": 40, "height": 40},
    ]
    layout, meta = compute_legible_cell_layout(elems, inner_cols=30, inner_rows=10)
    assert meta["mode"] == "legible"
    assert meta["rows"] == 2
    assert meta["cell_w"] >= 5
    assert meta["cell_h"] >= 3
    assert len(layout) == 3


def test_render_ascii_preserves_row_topology():
    from detection.ascii_ui_render import render_ascii_ui, select_elements_for_ascii_render

    ox, oy = 100, 100
    elems = [
        {
            "role": "Button", "name": "7", "automation_id": "n7",
            "x": ox + 20, "y": oy + 100, "width": 60, "height": 50,
        },
        {
            "role": "Button", "name": "8", "automation_id": "n8",
            "x": ox + 90, "y": oy + 100, "width": 60, "height": 50,
        },
        {
            "role": "Button", "name": "4", "automation_id": "n4",
            "x": ox + 20, "y": oy + 160, "width": 60, "height": 50,
        },
    ]
    filtered = select_elements_for_ascii_render(elems, ox, oy, 320, 280, min_pixels=8)
    result = render_ascii_ui(
        filtered, ox, oy, 320, 280, cols=48, height=20, preserve_aspect=True,
    )
    by_aid = {e["automation_id"]: e for e in result["elements"]}
    assert by_aid["n7"]["grid_bounds"][1] < by_aid["n4"]["grid_bounds"][1]
    assert by_aid["n7"]["grid_bounds"][1] == by_aid["n8"]["grid_bounds"][1]
    assert by_aid["n7"]["grid_bounds"][0] < by_aid["n8"]["grid_bounds"][0]


def test_render_ascii_stretch_mode_independent_axes():
    from detection.ascii_ui_render import render_ascii_ui, select_elements_for_ascii_render

    elems = [
        {
            "role": "Button", "name": "sq", "automation_id": "sq",
            "x": 110, "y": 110, "width": 50, "height": 50,
            "is_keyboard_focusable": True,
        },
    ]
    filtered = select_elements_for_ascii_render(elems, 100, 100, 200, 200, min_pixels=4)
    result = render_ascii_ui(
        filtered, 100, 100, 200, 200, cols=62, height=22, layout_mode="stretch",
    )
    assert result["viewport"]["mode"] == "stretch"


def test_render_ascii_row_gap_matches_screen_ratio():
    from detection.ascii_ui_render import render_ascii_ui, select_elements_for_ascii_render

    ox, oy = 100, 100
    elems = [
        {
            "role": "Button",
            "name": "7",
            "automation_id": "n7",
            "x": ox + 20,
            "y": oy + 100,
            "width": 60,
            "height": 50,
        },
        {
            "role": "Button",
            "name": "4",
            "automation_id": "n4",
            "x": ox + 20,
            "y": oy + 160,
            "width": 60,
            "height": 50,
        },
    ]
    filtered = select_elements_for_ascii_render(elems, ox, oy, 320, 280, min_pixels=8)
    legible = render_ascii_ui(
        filtered, ox, oy, 320, 280, cols=72, height=24, layout_mode="legible",
    )
    stretch = render_ascii_ui(
        filtered, ox, oy, 320, 280, cols=72, height=24, layout_mode="stretch",
    )
    by_leg = {e["automation_id"]: e for e in legible["elements"]}
    row_gap_leg = by_leg["n4"]["grid_bounds"][1] - by_leg["n7"]["grid_bounds"][1]
    by_str = {e["automation_id"]: e for e in stretch["elements"]}
    row_gap_str = by_str["n4"]["grid_bounds"][1] - by_str["n7"]["grid_bounds"][1]
    assert row_gap_leg >= 1
    assert row_gap_str >= 1


def test_do_ascii_ui_view_mocked():
    elements = _calc_like_elements()

    class _FakeListing:
        def get(self, k, d=None):
            return {
                "elements": elements,
                "backend_used": "uia",
                "list_ms": 42,
            }.get(k, d)

    with __import__("unittest.mock").mock.patch(
        "tools.ui_automation.do_list_elements", return_value=_FakeListing()
    ):
        with __import__("unittest.mock").mock.patch(
            "tools.windows.resolve_window_visual_rect",
            return_value={"x": 100, "y": 100, "width": 320, "height": 280, "title": "Calculadora"},
        ):
            with __import__("unittest.mock").mock.patch(
                "tools.ui_automation.do_get_focused_element",
                return_value={"found": True, "element": elements[1]},
            ):
                from tools.ascii_view import do_ascii_ui_view

                out = do_ascii_ui_view(window_title="Calculadora", width=72, height=22)
    assert out["success"]
    assert "7" in out["ascii"] or any(e.get("automation_id") == "num7Button" for e in out["elements"])
    assert any(e.get("key") == "e2" for e in out["elements"])
    focused = [e for e in out["elements"] if e.get("focused")]
    assert focused and focused[0]["automation_id"] == "num7Button"


def test_wide_control_not_interleaved_with_keypad_row():
    from detection.ascii_ui_render import _elem_key, compute_legible_cell_layout

    elems = [
        {
            "role": "Button", "name": "7", "automation_id": "n7",
            "x": 120, "y": 200, "width": 60, "height": 50,
        },
        {
            "role": "ListItem", "name": "Navigation", "automation_id": "wideNavStrip",
            "x": 140, "y": 198, "width": 312, "height": 36,
        },
        {
            "role": "Button", "name": "8", "automation_id": "n8",
            "x": 190, "y": 200, "width": 60, "height": 50,
        },
    ]
    layout, meta = compute_legible_cell_layout(elems, inner_cols=40, inner_rows=16)
    n7 = layout[_elem_key(elems[0])]
    nav = layout[_elem_key(elems[1])]
    n8 = layout[_elem_key(elems[2])]
    assert n7[1] == n8[1]
    assert nav[1] != n7[1]
    assert n7[0] < n8[0]


def test_split_band_by_x_gap():
    from detection.ascii_ui_render import _split_band_by_spatial_clusters

    left = ({"x": 10, "width": 40, "y": 100, "height": 40}, 30.0, 120.0)
    right = ({"x": 200, "width": 40, "y": 100, "height": 40}, 220.0, 120.0)
    rows = _split_band_by_spatial_clusters([left, right], median_w=50)
    assert len(rows) == 2
    assert len(rows[0]) == 1 and len(rows[1]) == 1


def test_compact_label_from_automation_id():
    from detection.ascii_ui_render import _compact_label

    assert _compact_label({"role": "Button", "name": "Siete", "automation_id": "num7Button"}) == "7"
    assert _compact_label({"role": "Button", "name": "Más", "automation_id": "plusButton"}) == "+"
    assert _compact_label({"role": "Text", "name": "Se muestra 0", "automation_id": "CalculatorResults"}) == "0"


def test_horizontal_chrome_filtered():
    from detection.ascii_ui_render import filter_elements_for_ascii

    elems = [
        {
            "role": "Button", "name": "Siguiente", "automation_id": "SectionOneNextButton",
            "x": 100, "y": 200, "width": 120, "height": 28,
        },
        {
            "role": "Button", "name": "Siete", "automation_id": "num7Button",
            "x": 100, "y": 250, "width": 60, "height": 60,
        },
        {
            "role": "Button", "name": "Ocho", "automation_id": "num8Button",
            "x": 170, "y": 250, "width": 60, "height": 60,
        },
        {
            "role": "Button", "name": "Nueve", "automation_id": "num9Button",
            "x": 240, "y": 250, "width": 60, "height": 60,
        },
    ]
    out = filter_elements_for_ascii(elems, 0, 0, 400, 400)
    aids = {e["automation_id"] for e in out}
    assert "SectionOneNextButton" not in aids
    assert "num7Button" in aids


def test_compact_layout_memory_row_single_line():
    from detection.ascii_ui_render import _elem_key, compute_compact_cell_layout

    aids = [
        "ClearMemoryButton", "MemRecall", "MemPlus", "MemMinus", "memButton", "MemoryButton",
    ]
    buttons = [
        {
            "role": "Button", "name": "m", "automation_id": aid,
            "x": 100 + i * 65, "y": 200, "width": 60, "height": 38,
        }
        for i, aid in enumerate(aids)
    ]
    layout, meta = compute_compact_cell_layout(buttons, 72, 18, 100, 200, 400)
    assert meta.get("layout") == "compact"
    row_ys = {layout[_elem_key(b)][1] for b in buttons if _elem_key(b) in layout}
    assert len(row_ys) == 1
    widths = [layout[_elem_key(b)][2] - layout[_elem_key(b)][0] + 1 for b in buttons if _elem_key(b) in layout]
    assert len(widths) >= 5
    assert all(w <= 8 for w in widths)


def test_dedupe_row_peers_overlapping_label():
    from detection.ascii_ui_render import _dedupe_row_peers

    a = ({"role": "Button", "name": "Dup", "width": 60, "height": 40, "x": 100}, 130.0, 200.0)
    b = ({"role": "Button", "name": "Dup", "width": 60, "height": 40, "x": 120}, 150.0, 200.0)
    out = _dedupe_row_peers([a, b])
    assert len(out) == 1


def test_render_ascii_use_colors_adds_ansi():
    from detection.ascii_ui_render import render_ascii_ui, select_elements_for_ascii_render

    elems = _calc_like_elements()[:2]
    filtered = select_elements_for_ascii_render(elems, 100, 100, 320, 280, min_pixels=8)
    plain = render_ascii_ui(
        filtered, 100, 100, 320, 280, cols=60, height=18, use_colors=False
    )
    colored = render_ascii_ui(
        filtered, 100, 100, 320, 280, cols=60, height=18, use_colors=True
    )
    assert "\033[" not in plain["ascii"]
    assert "\033[" in colored["ascii"] or "\033[" in colored["legend"]

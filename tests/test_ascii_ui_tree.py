"""Tests for ASCII UI tree (containment + occlusion)."""
from __future__ import annotations


def test_leaf_skips_text_container_with_button_inside():
    from detection.ascii_ui_render import select_elements_for_ascii_render

    elements = [
        {"role": "Text", "name": "Nav chrome", "automation_id": "", "x": 10, "y": 10, "width": 200, "height": 80},
        {"role": "Button", "name": "7", "automation_id": "num7", "x": 30, "y": 30, "width": 40, "height": 30},
    ]
    out = select_elements_for_ascii_render(elements, 0, 0, 300, 300, basic_only=True)
    names = [e.get("name") for e in out]
    assert "7" in names
    assert "Nav chrome" not in names


def test_occlusion_prune_drops_fully_covered_root_sibling():
    from detection.ascii_ui_tree import prepare_elements_for_render

    roles = frozenset({"Button"})
    elements = [
        {"role": "Button", "name": "Back", "x": 10, "y": 10, "width": 80, "height": 30},
        {"role": "Button", "name": "Front", "x": 10, "y": 10, "width": 80, "height": 30},
    ]
    pruned = prepare_elements_for_render(elements, roles, occlusion_prune=True)
    assert len(pruned) == 1
    assert pruned[0]["name"] == "Front"

    all_kept = prepare_elements_for_render(elements, roles, occlusion_prune=False)
    assert len(all_kept) >= 1


def test_display_and_buttons_both_kept_when_not_nested():
    from detection.ascii_ui_render import select_elements_for_ascii_render

    ox, oy = 100, 100
    elements = [
        {
            "role": "Text",
            "name": "Display 0",
            "automation_id": "CalculatorResults",
            "x": ox + 20,
            "y": oy + 20,
            "width": 280,
            "height": 50,
        },
        {
            "role": "Button",
            "name": "7",
            "automation_id": "num7Button",
            "x": ox + 20,
            "y": oy + 100,
            "width": 60,
            "height": 50,
        },
    ]
    out = select_elements_for_ascii_render(elements, ox, oy, 320, 280, basic_only=True)
    aids = {e.get("automation_id") for e in out}
    assert "CalculatorResults" in aids
    assert "num7Button" in aids

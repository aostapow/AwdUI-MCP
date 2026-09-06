"""Tests for adaptive spatial content clustering."""
from detection.element_model import DetectedElement
from detection.spatial_cluster import (
    filter_by_content_cluster,
    infer_content_region,
)


def _scope():
    return {
        "window_title": "App",
        "visual": {"x": 100, "y": 100, "w": 500, "h": 700},
        "client": {"x": 100, "y": 100, "w": 500, "h": 700},
        "process_ids": {1},
    }


def _btn(aid: str, x: int, y: int) -> DetectedElement:
    return DetectedElement(
        name=aid,
        role="Button",
        automation_id=aid,
        x=x,
        y=y,
        width=60,
        height=50,
        process_id=1,
    )


def test_infer_content_region_keypad_cluster():
    scope = _scope()
    keypad = [
        _btn("n7", 200, 300),
        _btn("n8", 270, 300),
        _btn("n9", 340, 300),
        _btn("n4", 200, 360),
        _btn("n5", 270, 360),
        _btn("n6", 340, 360),
    ]
    nav = DetectedElement(
        name="Nav",
        role="ListItem",
        automation_id="navWide",
        x=110,
        y=298,
        width=312,
        height=36,
        process_id=1,
    )
    region = infer_content_region(keypad + [nav], scope=scope, min_elements=6)
    assert region is not None
    assert region["x"] >= 175
    assert region["w"] < 400


def test_filter_drops_nav_outlier():
    scope = _scope()
    elems = [
        _btn("n7", 200, 300),
        _btn("n8", 270, 300),
        _btn("n9", 340, 300),
        _btn("n4", 200, 360),
        _btn("n5", 270, 360),
        _btn("n6", 340, 360),
        DetectedElement(
            name="Nav",
            role="ListItem",
            automation_id="navWide",
            x=110,
            y=298,
            width=312,
            height=36,
            process_id=1,
        ),
    ]
    with __import__("unittest.mock").mock.patch(
        "detection.element_coords.to_screen_coords",
        side_effect=lambda e, _t: e,
    ):
        kept, removed, region = filter_by_content_cluster(elems, scope)
    assert removed >= 1
    assert "navWide" not in {e.automation_id for e in kept}
    assert region is not None


def test_too_few_elements_skips_cluster():
    scope = _scope()
    elems = [_btn("a", 200, 300), _btn("b", 270, 300)]
    kept, removed, region = filter_by_content_cluster(elems, scope)
    assert kept == elems
    assert removed == 0

"""Tests for UIA element deduplication (UWP overlay trees)."""
from detection.element_dedupe import dedupe_detected_elements
from detection.element_model import DetectedElement


def _btn(aid: str, x: int, y: int, w: int = 98, h: int = 63, enabled: bool = True) -> DetectedElement:
    return DetectedElement(
        name=aid,
        role="Button",
        automation_id=aid,
        framework_id="XAML",
        x=x,
        y=y,
        width=w,
        height=h,
        enabled=enabled,
    )


def test_dedupe_same_automation_id_keeps_larger_enabled():
    dup = _btn("num5Button", 212, 783)
    overlay = _btn("num5Button", 268, 944, w=78, h=50)
    out = dedupe_detected_elements([dup, overlay])
    aids = [e.automation_id for e in out]
    assert aids.count("num5Button") == 1
    kept = next(e for e in out if e.automation_id == "num5Button")
    assert kept.x == 212


def test_dedupe_prefers_enabled_over_disabled():
    disabled = _btn("clearButton", 250, 467, enabled=False)
    enabled = _btn("clearButton", 312, 584, enabled=True)
    out = dedupe_detected_elements([disabled, enabled])
    kept = next(e for e in out if e.automation_id == "clearButton")
    assert kept.enabled is True
    assert kept.x == 312


def test_dedupe_preserves_unique_automation_ids():
    elems = [_btn("num1Button", 1, 1), _btn("num2Button", 2, 2), _btn("num3Button", 3, 3)]
    out = dedupe_detected_elements(elems)
    assert len(out) == 3

"""UWP visual rect and element scope filtering."""
from __future__ import annotations

from detection.element_coords import element_center_in_rect


def test_element_center_in_rect():
    rect = {"x": 100, "y": 300, "w": 400, "h": 600}
    assert element_center_in_rect({"x": 150, "y": 700, "width": 50, "height": 40}, rect)
    assert not element_center_in_rect({"x": 0, "y": 50, "width": 40, "height": 40}, rect)


def test_resolve_window_visual_rect_prefers_frame_host():
    from unittest import mock

    from tools.windows import resolve_window_visual_rect

    windows = [
        {
            "title": "Sample UWP",
            "process_name": "SampleApp.exe",
            "x": 0,
            "y": 1,
            "width": 400,
            "height": 665,
        },
        {
            "title": "Sample UWP",
            "process_name": "ApplicationFrameHost.exe",
            "x": 98,
            "y": 318,
            "width": 425,
            "height": 675,
        },
    ]
    with mock.patch("tools.windows.do_list_windows", return_value=windows):
        rect = resolve_window_visual_rect("Sample UWP")
    assert rect is not None
    assert rect["w"] >= 425
    assert rect["h"] >= 675


def test_best_window_candidate_prefers_application_frame_for_uwp_pair():
    from tools.windows import _best_window_candidate

    windows = [
        {
            "title": "Sample UWP",
            "process_name": "SampleApp.exe",
            "x": 0,
            "y": 1,
            "width": 400,
            "height": 665,
        },
        {
            "title": "Sample UWP",
            "process_name": "ApplicationFrameHost.exe",
            "x": 98,
            "y": 318,
            "width": 425,
            "height": 675,
        },
    ]
    best = _best_window_candidate(windows, "sample uwp", purpose="visual")
    assert "applicationframehost" in (best.get("process_name") or "").lower()

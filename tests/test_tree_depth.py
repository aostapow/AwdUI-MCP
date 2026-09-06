"""Tests for dynamic tree depth normalization."""
from detection.tree_depth import (
    ASCII_UI_DEFAULT_MAX_DEPTH,
    FRAMEWORK_AUTO_DEPTH,
    LIST_ELEMENTS_DEFAULT_MAX_DEPTH,
    OBSERVE_UI_MAX_DEPTH,
    UNLIMITED_DEPTH,
    depth_exceeded,
    format_depth_header,
    framework_auto_depth,
    normalize_tree_depth,
    resolve_list_depth,
)


def test_defaults_are_auto():
    assert LIST_ELEMENTS_DEFAULT_MAX_DEPTH == 0
    assert ASCII_UI_DEFAULT_MAX_DEPTH == 0
    assert OBSERVE_UI_MAX_DEPTH == 8


def test_normalize_zero_is_auto_sentinel():
    assert normalize_tree_depth(0) == 0
    assert normalize_tree_depth(None) == 0


def test_normalize_negative_unlimited():
    assert normalize_tree_depth(-1) == UNLIMITED_DEPTH


def test_normalize_positive_unchanged():
    assert normalize_tree_depth(5) == 5
    assert normalize_tree_depth(12) == 12


def test_depth_exceeded_unlimited_never_stops():
    assert depth_exceeded(500, UNLIMITED_DEPTH) is False


def test_depth_exceeded_limited():
    assert depth_exceeded(3, 5) is False
    assert depth_exceeded(6, 5) is True


def test_framework_auto_depth_uwp():
    assert framework_auto_depth("uwp") == FRAMEWORK_AUTO_DEPTH["uwp"]
    assert framework_auto_depth("win32") == 12


def test_resolve_list_depth_auto_framework():
    req, eff, fw = resolve_list_depth(0, framework="uwp")
    assert req == 0
    assert eff == 32
    assert fw == "uwp"


def test_resolve_list_depth_explicit_overrides():
    req, eff, fw = resolve_list_depth(5, framework="uwp")
    assert req == 5
    assert eff == 5
    assert fw == ""


def test_resolve_list_depth_unlimited():
    req, eff, _ = resolve_list_depth(-1)
    assert req == -1
    assert eff == UNLIMITED_DEPTH


def test_resolve_list_depth_role_boost():
    req, eff, _ = resolve_list_depth(0, framework="win32", role="Button")
    assert req == 0
    assert eff >= 12


def test_format_depth_header():
    assert "auto/uwp" in format_depth_header(0, 32, "uwp")
    assert format_depth_header(8, 8) == "depth=8"
    assert format_depth_header(-1, UNLIMITED_DEPTH) == "depth=full"

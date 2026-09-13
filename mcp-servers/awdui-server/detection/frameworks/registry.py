"""Resolve FrameworkProfile from detect_framework labels."""
from __future__ import annotations

from typing import Optional

from detection.frameworks.base import FrameworkProfile

_DEFAULT = FrameworkProfile(
    key="unknown",
    auto_list_depth=20,
    backend_order=("uia", "flaui", "msaa", "win32", "jab"),
)

_PROFILES: dict[str, FrameworkProfile] = {
    "uwp": FrameworkProfile(
        key="uwp",
        aliases=("winui",),
        auto_list_depth=32,
        backend_order=("flaui", "uia", "msaa"),
        prefers_spy_invoke=True,
        prefers_spy_expand_collapse=True,
        expander_dims_via_spy=True,
        quick_resolve_spy_before_find=False,
    ),
    "wpf": FrameworkProfile(
        key="wpf",
        auto_list_depth=24,
        backend_order=("uia", "flaui", "msaa"),
    ),
    "winforms": FrameworkProfile(
        key="winforms",
        auto_list_depth=16,
        backend_order=("flaui", "uia", "msaa"),
    ),
    "win32": FrameworkProfile(
        key="win32",
        auto_list_depth=12,
        backend_order=("uia", "msaa", "win32"),
        quick_resolve_spy_before_find=True,
    ),
    "mfc": FrameworkProfile(
        key="mfc",
        auto_list_depth=12,
        backend_order=("uia", "msaa", "win32"),
        quick_resolve_spy_before_find=True,
    ),
    "qt": FrameworkProfile(
        key="qt",
        auto_list_depth=20,
        backend_order=("uia", "flaui", "msaa"),
        quick_resolve_spy_before_find=True,
    ),
    "electron": FrameworkProfile(
        key="electron",
        auto_list_depth=28,
        backend_order=("uia", "flaui", "msaa"),
        quick_resolve_spy_before_find=True,
    ),
    "chromium_browser": FrameworkProfile(
        key="chromium_browser",
        auto_list_depth=28,
        backend_order=("uia", "flaui", "msaa"),
        quick_resolve_spy_before_find=True,
    ),
    "java_swing": FrameworkProfile(
        key="java_swing",
        auto_list_depth=24,
        backend_order=("jab", "uia"),
    ),
    "java_fx": FrameworkProfile(
        key="java_fx",
        auto_list_depth=20,
        backend_order=("uia", "jab"),
    ),
    "gtk": FrameworkProfile(
        key="gtk",
        auto_list_depth=10,
        backend_order=(),
    ),
    "unknown": _DEFAULT,
}


def normalize_framework_key(framework: Optional[str]) -> str:
    key = (framework or "unknown").strip().lower()
    if key == "winui":
        return "uwp"
    if key in _PROFILES:
        return key
    return "unknown"


def get_profile(framework: Optional[str]) -> FrameworkProfile:
    return _PROFILES.get(normalize_framework_key(framework), _DEFAULT)


def get_profile_for_window(window_title: Optional[str] = None) -> FrameworkProfile:
    try:
        from tools.framework_detect import do_detect_framework

        fw = do_detect_framework(window_title).get("framework", "unknown")
    except Exception:
        fw = "unknown"
    return get_profile(fw)


def framework_auto_depth_map() -> dict[str, int]:
    """Depth table for max_depth=0 (tree_depth + docs)."""
    out: dict[str, int] = {}
    for key, profile in _PROFILES.items():
        out[key] = profile.auto_list_depth
    out["winui"] = _PROFILES["uwp"].auto_list_depth
    return out

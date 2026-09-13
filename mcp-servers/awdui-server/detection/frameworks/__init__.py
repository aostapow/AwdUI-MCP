"""Per-framework detection policies (not per-app)."""
from detection.frameworks.base import FrameworkProfile
from detection.frameworks.registry import (
    framework_auto_depth_map,
    get_profile,
    get_profile_for_window,
    normalize_framework_key,
)

__all__ = [
    "FrameworkProfile",
    "framework_auto_depth_map",
    "get_profile",
    "get_profile_for_window",
    "normalize_framework_key",
]

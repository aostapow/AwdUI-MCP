"""Tree walk depth: 0 = auto by framework, negative = unlimited, positive = explicit cap."""
from __future__ import annotations

import time
from typing import Optional

# MCP defaults: 0 → framework-adaptive depth (see FRAMEWORK_AUTO_DEPTH).
LIST_ELEMENTS_DEFAULT_MAX_DEPTH = 0
SPY_TREE_DEFAULT_MAX_DEPTH = 0
ASCII_UI_DEFAULT_MAX_DEPTH = 0

# Fast observation paths — never inherit auto/framework default.
OBSERVE_UI_MAX_DEPTH = 8
OBSERVE_UI_MAX_ELEMENTS = 80
FINGERPRINT_MAX_DEPTH = 3

UNLIMITED_DEPTH = 9999

# Auto depth when max_depth=0 (framework detected via detect_framework).
FRAMEWORK_AUTO_DEPTH: dict[str, int] = {
    "uwp": 32,
    "winui": 32,
    "wpf": 24,
    "winforms": 16,
    "qt": 20,
    "electron": 28,
    "chromium_browser": 28,
    "java_swing": 24,
    "java_fx": 20,
    "win32": 12,
    "gtk": 10,
    "unknown": 20,
}
DEFAULT_AUTO_DEPTH = 20

_MENU_ROLES = frozenset({"menuitem", "menu", "menubar"})
_MENU_ROLE_MAX_DEPTH = {
    "menuitem": 6,
    "menu": 6,
    "menubar": 4,
}
_WIN32_ROLE_FILTER_CAP = 20

_FW_CACHE: dict[str, tuple[float, str]] = {}
_FW_CACHE_TTL = 30.0


def framework_auto_depth(framework: Optional[str]) -> int:
    """Depth cap for max_depth=0 from detected UI framework."""
    key = (framework or "unknown").strip().lower()
    return FRAMEWORK_AUTO_DEPTH.get(key, DEFAULT_AUTO_DEPTH)


def _detect_framework(window_title: Optional[str]) -> str:
    cache_key = (window_title or "").strip().lower() or "__foreground__"
    now = time.monotonic()
    cached = _FW_CACHE.get(cache_key)
    if cached and now - cached[0] < _FW_CACHE_TTL:
        return cached[1]
    fw = "unknown"
    try:
        from tools.framework_detect import do_detect_framework

        fw = str(do_detect_framework(window_title or None).get("framework") or "unknown")
    except Exception:
        pass
    _FW_CACHE[cache_key] = (now, fw)
    return fw


def normalize_tree_depth(max_depth: Optional[int]) -> int:
    """Normalize depth for low-level walkers.

    0 = auto (caller should use resolve_list_depth).
    <0 = unlimited.
    >0 = explicit cap.
    """
    if max_depth is None:
        return 0
    md = int(max_depth)
    if md < 0:
        return UNLIMITED_DEPTH
    return md


def depth_exceeded(current_depth: int, max_depth: int) -> bool:
    """True when current_depth is past the effective cap."""
    if max_depth >= UNLIMITED_DEPTH:
        return False
    if max_depth <= 0:
        return False
    return current_depth > max_depth


def resolve_list_depth(
    max_depth: Optional[int] = None,
    *,
    role: Optional[str] = None,
    window_title: Optional[str] = None,
    framework: Optional[str] = None,
) -> tuple[int, int, str]:
    """Return (requested, effective, framework_used) for list/spy walks."""
    requested = int(max_depth if max_depth is not None else LIST_ELEMENTS_DEFAULT_MAX_DEPTH)
    framework_used = ""

    if requested > 0:
        effective = requested
    elif requested < 0:
        effective = UNLIMITED_DEPTH
    else:
        framework_used = (framework or _detect_framework(window_title)).strip().lower() or "unknown"
        effective = framework_auto_depth(framework_used)

    # Role-filtered walks: shallow caps for menus; modest bump for other roles.
    if role and effective < UNLIMITED_DEPTH:
        role_lower = role.strip().lower()
        if role_lower in _MENU_ROLES:
            cap = _MENU_ROLE_MAX_DEPTH.get(role_lower, 6)
            effective = min(effective, cap)
        elif framework_used == "win32":
            effective = min(max(effective, effective + 2), _WIN32_ROLE_FILTER_CAP)
        else:
            effective = max(effective, min(effective + 8, 48))

    return requested, effective, framework_used


def format_depth_header(requested: int, effective: int, framework: str = "") -> str:
    """Short depth note for tool text headers."""
    if requested > 0:
        return f"depth={requested}"
    if requested < 0:
        return "depth=full"
    fw = (framework or "unknown").strip()
    return f"depth=auto/{fw}→{effective}"

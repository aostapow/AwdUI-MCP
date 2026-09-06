"""Per-HWND UIA descendant cache (short TTL, invalidated on stale reads)."""
from __future__ import annotations

import time
from typing import Any, Callable, Optional

_cache: dict[tuple[int, str], tuple[float, Any]] = {}


def get_descendants(
    hwnd: int,
    fetch: Callable[[], Any],
    scope: str = "default",
    ttl_s: float = 30.0,
) -> Any:
    """Return cached descendants for *hwnd* when within *ttl_s*."""
    key = (int(hwnd), str(scope or "default"))
    now = time.monotonic()
    hit = _cache.get(key)
    if hit is not None:
        ts, value = hit
        if now - ts < float(ttl_s):
            return value
    value = fetch()
    _cache[key] = (now, value)
    return value


def invalidate(hwnd: int, scope: str = "default") -> None:
    _cache.pop((int(hwnd), str(scope or "default")), None)


def invalidate_all() -> int:
    n = len(_cache)
    _cache.clear()
    return n

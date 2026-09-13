"""Mutually exclusive automation_id pairs after state toggles (generic UWP/chrome)."""
from __future__ import annotations

# Primary id -> alternate ids visible after invoke/toggle
TOGGLE_ALIASES: dict[str, list[str]] = {
    "NormalAlwaysOnTopButton": ["ExitAlwaysOnTopButton"],
    "ExitAlwaysOnTopButton": ["NormalAlwaysOnTopButton"],
}


def alias_candidates(automation_id: str | None) -> list[str]:
    """Ordered ids to try: primary first, then known post-toggle alternates."""
    aid = (automation_id or "").strip()
    if not aid:
        return []
    out: list[str] = [aid]
    for alt in TOGGLE_ALIASES.get(aid, []):
        if alt not in out:
            out.append(alt)
    return out

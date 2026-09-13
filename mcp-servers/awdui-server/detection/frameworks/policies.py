"""Shared policy helpers for framework profiles."""
from __future__ import annotations

from typing import Any, Sequence

_UWP_KEYS = frozenset({"uwp", "winui"})


def weak_backend_result(
    profile_key: str,
    backend_name: str,
    elements: Sequence[Any],
) -> bool:
    key = (profile_key or "").lower()
    if key in _UWP_KEYS and backend_name == "flaui":
        aids = sum(1 for e in elements if getattr(e, "automation_id", ""))
        if aids < 15:
            return True
    if key not in _UWP_KEYS or backend_name != "msaa":
        return False
    if not elements or len(elements) > 2:
        return False
    shell_roles = {"Role_10", "Pane", "Client", "Window", "Dialog"}
    return all(
        not (getattr(elem, "automation_id", "") or "")
        and (getattr(elem, "role", "") or "") in shell_roles
        for elem in elements
    )

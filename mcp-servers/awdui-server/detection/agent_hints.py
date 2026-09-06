"""Parse agent_hints text from the object repository (app-agnostic)."""
from __future__ import annotations

import json
import re
from typing import Any, Optional


def parse_agent_hints(hints: str) -> dict[str, Any]:
    """Parse agent_hints: JSON object or ``key: value`` lines."""
    text = (hints or "").strip()
    if not text:
        return {}
    if text.startswith("{"):
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return {str(k).lower(): v for k, v in data.items()}
        except json.JSONDecodeError:
            pass
    out: dict[str, Any] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        norm = re.sub(r"\s+", "_", key.strip().lower())
        out[norm] = value.strip()
    return out


def hint_verify_automation_id(hints: str) -> Optional[str]:
    """Return verify target automation_id from repo hints, if any."""
    parsed = parse_agent_hints(hints)
    for key in ("verify_automation_id", "verify_target", "verify_display"):
        val = parsed.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None

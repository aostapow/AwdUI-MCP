"""Parse agent_hints text from the object repository (app-agnostic)."""
from __future__ import annotations

import json
import re
from typing import Any, Optional

# MCP tools that hints may reference (app-agnostic).
_KNOWN_TOOLS: tuple[str, ...] = (
    "invoke_element",
    "click_element",
    "double_click_element",
    "right_click_element",
    "select_control_item",
    "list_control_items",
    "set_element_value",
    "type_into_element",
    "expand_element",
    "expand_collapse_element",
    "find_element",
    "repo_action",
    "repo_find",
    "read_element",
    "get_element_properties",
    "spy_inspect",
    "send_keys",
    "press_key",
    "press_key_combo",
    "scroll_element",
    "select_option",
)

_PREFERRED_TOOL_KEYS: tuple[str, ...] = (
    "metodo_preferido",
    "preferred_tool",
    "mcp_tool",
    "tool",
)

_CLICK_MODE_TOOLS: frozenset[str] = frozenset(
    {"click_element", "click", "coordinates", "coords", "coordinate_click"}
)
_INVOKE_MODE_TOOLS: frozenset[str] = frozenset(
    {"invoke_element", "invoke", "invokepattern", "invoke_pattern"}
)


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


def _normalize_tool_token(value: str) -> str:
    raw = (value or "").strip().lower().replace("-", "_")
    if not raw:
        return ""
    for sep in ("|", ";", ","):
        if sep in raw:
            raw = raw.split(sep, 1)[0].strip()
    if " si " in raw:
        raw = raw.split(" si ", 1)[0].strip()
    raw = raw.replace(" ", "_")
    for tool in _KNOWN_TOOLS:
        if tool in raw or raw == tool:
            return tool
    return raw


def hint_preferred_tool(hints: str) -> Optional[str]:
    """Return preferred MCP tool name from repo hints, if any."""
    parsed = parse_agent_hints(hints)
    for key in _PREFERRED_TOOL_KEYS:
        val = parsed.get(key)
        if isinstance(val, str) and val.strip():
            token = _normalize_tool_token(val)
            if token in _KNOWN_TOOLS:
                return token
    return None


def hint_click_mode(hints: str) -> str:
    """How repo_action Click should behave: invoke, click, or auto (default)."""
    preferred = hint_preferred_tool(hints)
    if preferred in _CLICK_MODE_TOOLS:
        return "click"
    if preferred in _INVOKE_MODE_TOOLS:
        return "invoke"
    parsed = parse_agent_hints(hints)
    for key in ("avoid_invoke", "no_invoke", "skip_invoke"):
        val = str(parsed.get(key, "")).strip().lower()
        if val in ("true", "yes", "1", "si", "sí"):
            return "click"
    for key in ("prefer_invoke", "only_invoke"):
        val = str(parsed.get(key, "")).strip().lower()
        if val in ("true", "yes", "1", "si", "sí"):
            return "invoke"
    return "auto"


def hint_verify_automation_id(hints: str) -> Optional[str]:
    """Return verify target automation_id from repo hints, if any."""
    parsed = parse_agent_hints(hints)
    for key in ("verify_automation_id", "verify_target", "verify_display"):
        val = parsed.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None

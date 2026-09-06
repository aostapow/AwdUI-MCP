"""Official Microsoft UIA control-type map → MCP tool strategies (static JSON)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

_MAP_PATH = Path(__file__).resolve().parent / "data" / "uia_control_map.json"
_REFERENCE_PATH = Path(__file__).resolve().parent / "data" / "ms_uia_patterns_reference.json"


@lru_cache(maxsize=1)
def load_patterns_reference() -> dict[str, Any]:
    """Microsoft UIA pattern mapping only (no AwdUI strategies)."""
    data = json.loads(_REFERENCE_PATH.read_text(encoding="utf-8"))
    return {
        "schema_version": data.get("schema_version", 1),
        "source_url": data.get("source_url", ""),
        "controls": data.get("controls") or {},
    }


# Derived from ms_uia_patterns_reference.json — single source for MS control type names.
OFFICIAL_MS_CONTROL_TYPES = frozenset(load_patterns_reference()["controls"].keys())

# Repo-specific extensions allowed beyond Microsoft's list.
ALLOWED_EXTRA_CONTROL_TYPES = frozenset({"Custom"})

# Tools referenced in the map must exist in the MCP server catalog.
KNOWN_AWDUI_TOOLS = frozenset(
    {
        "click",
        "click_element",
        "clipboard",
        "discover_control_interaction",
        "drag",
        "expand_element",
        "find_item_by_property",
        "find_text",
        "focus_window",
        "get_element_properties",
        "get_grid_item",
        "invoke_element",
        "realize_virtualized_item",
        "list_control_items",
        "list_elements",
        "read_table",
        "select_control_item",
        "send_keys",
        "set_element_value",
        "set_target_window",
        "smart_find",
        "spy_inspect",
        "scroll",
        "scroll_element",
        "scroll_into_view",
        "type_text",
        "wait_for_condition",
        "wait_for_element",
        "wait_for_input_idle",
    }
)


@lru_cache(maxsize=1)
def load_control_map() -> dict[str, Any]:
    data = json.loads(_MAP_PATH.read_text(encoding="utf-8"))
    controls = data.get("controls") or {}
    return {
        "schema_version": data.get("schema_version", 0),
        "source_url": data.get("source_url", ""),
        "controls": controls,
    }


def list_control_types() -> list[str]:
    return sorted(load_control_map()["controls"].keys())


def get_control_spec(role: str) -> Optional[dict[str, Any]]:
    key = (role or "").strip()
    if not key:
        return None
    controls = load_control_map()["controls"]
    if key in controls:
        return controls[key]
    # UIA sometimes returns "ControlType.Button" style — normalize
    short = key.replace("ControlType.", "")
    return controls.get(short)


def _pattern_match(entry_patterns: list[str], live_patterns: set[str]) -> bool:
    if not entry_patterns:
        return True
    if not live_patterns:
        return True
    return bool(set(entry_patterns) & live_patterns)


def _entry_to_strategy(entry: dict, phase: str, confidence: str) -> dict:
    # Official map is secondary to runtime heuristics in control_interaction.
    if phase == "act":
        confidence = "low"
    return {
        "id": entry.get("id", "map_unknown"),
        "tools": list(entry.get("tools") or []),
        "steps": list(entry.get("steps") or []),
        "confidence": confidence,
        "note": "Microsoft UIA control map",
        "phase": phase,
        "source": "uia_control_map",
    }


def official_strategies(role: str, live_patterns: Optional[set[str]] = None) -> list[dict]:
    """Build strategy dicts from static MS map filtered by live patterns."""
    spec = get_control_spec(role)
    if not spec:
        return []
    pats = live_patterns or set()
    strategies: list[dict] = []

    for tool in spec.get("read") or []:
        strategies.append(
            {
                "id": f"map_read_{tool}",
                "tools": [tool],
                "steps": [f"Read via {tool} (MS map)"],
                "confidence": "high",
                "phase": "read",
                "source": "uia_control_map",
            }
        )

    for entry in spec.get("act") or []:
        entry_pats = list(entry.get("patterns") or [])
        if not _pattern_match(entry_pats, pats):
            continue
        conf = "high" if (entry_pats and pats and set(entry_pats) & pats) else "medium"
        strategies.append(_entry_to_strategy(entry, "act", conf))

    fallback_tools = list(spec.get("fallback") or [])
    if fallback_tools:
        strategies.append(
            {
                "id": "map_fallback",
                "tools": fallback_tools,
                "steps": ["Fallback when primary UIA patterns fail (MS map)"],
                "confidence": "low",
                "phase": "fallback",
                "source": "uia_control_map",
            }
        )

    return strategies


def merge_official_strategies(
    strategies: list[dict],
    role: str,
    live_patterns: set[str],
) -> dict[str, Any]:
    """Append official map strategies; return metadata for report."""
    official = official_strategies(role, live_patterns)
    seen = {s["id"] for s in strategies}
    added = 0
    for item in official:
        if item["id"] in seen:
            continue
        strategies.append(item)
        seen.add(item["id"])
        added += 1
    spec = get_control_spec(role)
    meta = {
        "role": role,
        "in_map": spec is not None,
        "strategies_added": added,
        "patterns_ms": (spec or {}).get("patterns_ms"),
        "source_url": load_control_map().get("source_url", ""),
    }
    return meta


def format_map_note(meta: dict) -> str:
    if not meta.get("in_map"):
        return f"  (no official MS map entry for role={meta.get('role', '')})"
    pms = meta.get("patterns_ms") or {}
    must = pms.get("must") or []
    cond = pms.get("conditional") or []
    return (
        f"  MS map: must={must} conditional={cond} "
        f"(+{meta.get('strategies_added', 0)} strategies from uia_control_map.json)"
    )


def validate_control_map(raw: Optional[dict[str, Any]] = None) -> list[str]:
    """Return validation errors (empty list = OK)."""
    errors: list[str] = []
    if raw is None:
        raw = json.loads(_MAP_PATH.read_text(encoding="utf-8"))

    if not raw.get("schema_version"):
        errors.append("missing schema_version")
    if not raw.get("source_url"):
        errors.append("missing source_url")

    controls = raw.get("controls")
    if not isinstance(controls, dict):
        errors.append("controls must be an object")
        return errors

    present = set(controls.keys())
    missing_ms = sorted(OFFICIAL_MS_CONTROL_TYPES - present)
    if missing_ms:
        errors.append(f"missing official MS control types: {', '.join(missing_ms)}")

    unknown = sorted(present - OFFICIAL_MS_CONTROL_TYPES - ALLOWED_EXTRA_CONTROL_TYPES)
    if unknown:
        errors.append(f"unknown control types (not MS official): {', '.join(unknown)}")

    for role, spec in sorted(controls.items()):
        prefix = f"{role}:"
        if not isinstance(spec, dict):
            errors.append(f"{prefix} spec must be an object")
            continue

        pms = spec.get("patterns_ms")
        if not isinstance(pms, dict):
            errors.append(f"{prefix} missing patterns_ms")
        else:
            for key in ("must", "conditional", "not"):
                if key not in pms:
                    errors.append(f"{prefix} patterns_ms missing '{key}'")

        read_tools = list(spec.get("read") or [])
        act_entries = list(spec.get("act") or [])
        fallback_tools = list(spec.get("fallback") or [])
        if not read_tools and not act_entries and not fallback_tools and role not in ("Separator", "TitleBar"):
            errors.append(f"{prefix} must define read, act, or fallback tools")

        all_tools: set[str] = set(read_tools) | set(fallback_tools)
        for tool in all_tools:
            if tool not in KNOWN_AWDUI_TOOLS:
                errors.append(f"{prefix} unknown MCP tool '{tool}' in read/fallback")

        act_ids: set[str] = set()
        for entry in act_entries:
            if not isinstance(entry, dict):
                errors.append(f"{prefix} act entry must be an object")
                continue
            eid = entry.get("id") or ""
            if not eid:
                errors.append(f"{prefix} act entry missing id")
            elif eid in act_ids:
                errors.append(f"{prefix} duplicate act id '{eid}'")
            else:
                act_ids.add(eid)
            if not entry.get("tools"):
                errors.append(f"{prefix} act '{eid}' missing tools")
            if not entry.get("steps"):
                errors.append(f"{prefix} act '{eid}' missing steps")
            for tool in entry.get("tools") or []:
                if tool not in KNOWN_AWDUI_TOOLS:
                    errors.append(f"{prefix} act '{eid}' unknown MCP tool '{tool}'")

    return errors

"""Append-only property observations per repo object (success paths only)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Optional

OBSERVATION_KEYS = (
    "automation_id",
    "role",
    "class_name",
    "framework_id",
    "name",
    "localized_control_type",
    "process_id",
    "hwnd",
    "patterns",
    "value",
)

VOLATILE_KEYS = frozenset({"x", "y", "width", "height", "bbox", "clickable_x", "clickable_y"})

STABLE_THRESHOLD = 0.95
MIN_OBSERVATIONS = 3
MAX_OBSERVATIONS_PER_OBJECT = 200


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_properties(elem: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in OBSERVATION_KEYS:
        if key not in elem:
            continue
        val = elem.get(key)
        if val is None or val == "":
            continue
        if key == "patterns" and isinstance(val, (list, dict)):
            out[key] = json.dumps(val, sort_keys=True, ensure_ascii=False)
        else:
            out[key] = val
    return out


def compute_context_hash(
    *,
    app_id: str = "",
    framework: str = "",
    window_class: str = "",
    process_name: str = "",
) -> str:
    raw = "|".join(
        [
            (app_id or "").strip(),
            (framework or "").strip().lower(),
            (window_class or "").strip(),
            (process_name or "").strip().lower(),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def analyze_property_stability(
    observations: list[dict[str, Any]],
    *,
    context_hash: Optional[str] = None,
) -> dict[str, Any]:
    rows = observations
    if context_hash:
        rows = [r for r in rows if r.get("context_hash") == context_hash]
    if not rows:
        return {
            "stable": [],
            "volatile": [],
            "unknown": list(OBSERVATION_KEYS),
            "samples": 0,
            "distinct_runs": 0,
            "recommended_mandatory": {},
        }

    by_key: dict[str, list[str]] = {}
    run_ids: set[str] = set()
    for row in rows:
        if row.get("run_id"):
            run_ids.add(str(row["run_id"]))
        try:
            props = json.loads(row.get("properties_json") or "{}")
        except json.JSONDecodeError:
            continue
        for k, v in props.items():
            by_key.setdefault(k, []).append(str(v))

    stable: list[str] = []
    volatile: list[str] = []
    unknown: list[str] = []
    n = len(rows)

    for key in sorted(set(by_key) | set(OBSERVATION_KEYS)):
        if key in VOLATILE_KEYS:
            volatile.append(key)
            continue
        values = by_key.get(key) or []
        if len(values) < MIN_OBSERVATIONS:
            unknown.append(key)
            continue
        top = max(set(values), key=values.count)
        ratio = values.count(top) / len(values)
        if ratio >= STABLE_THRESHOLD:
            stable.append(key)
        else:
            volatile.append(key)

    recommended_mandatory: dict[str, str] = {}
    for k in stable:
        vals = by_key.get(k) or []
        if vals:
            recommended_mandatory[k] = max(set(vals), key=vals.count)

    return {
        "stable": stable,
        "volatile": volatile,
        "unknown": unknown,
        "samples": n,
        "distinct_runs": len(run_ids),
        "recommended_mandatory": recommended_mandatory,
    }

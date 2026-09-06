"""Sync uia_control_map.json with Microsoft UIA pattern reference (conservative merge)."""
from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

_DATA_DIR = Path(__file__).resolve().parent / "data"
_MAP_PATH = _DATA_DIR / "uia_control_map.json"
_REFERENCE_PATH = _DATA_DIR / "ms_uia_patterns_reference.json"
_MS_PATTERN_URL = (
    "https://learn.microsoft.com/en-us/dotnet/framework/ui-automation/"
    "control-pattern-mapping-for-ui-automation-clients"
)

# Types documented in Win32 overview but absent from the .NET pattern-mapping table.
_MANUAL_REFERENCE_TYPES = ("AppBar", "SemanticZoom")

_EMPTY_PATTERNS_MS: dict[str, list[str]] = {"must": [], "conditional": [], "not": []}


@dataclass
class SyncReport:
    missing_in_map: list[str] = field(default_factory=list)
    extra_in_map: list[str] = field(default_factory=list)
    patterns_drift: dict[str, tuple[dict, dict]] = field(default_factory=dict)

    @property
    def needs_apply(self) -> bool:
        return bool(self.missing_in_map)

    @property
    def has_warnings(self) -> bool:
        return bool(self.extra_in_map or self.patterns_drift)


def _normalize_control_type(name: str) -> str:
    return re.sub(r"\s+", "", (name or "").strip())


def _normalize_pattern_name(name: str) -> str:
    return re.sub(r"\s+", "", (name or "").strip())


def _parse_pattern_cell(cell: str) -> list[str]:
    text = (cell or "").strip()
    if not text or text.lower() == "none":
        return []
    parts = [p.strip() for p in text.split(",") if p.strip()]
    return [_normalize_pattern_name(p) for p in parts if _normalize_pattern_name(p)]


def parse_ms_pattern_table(markdown: str) -> dict[str, dict[str, list[str]]]:
    """Parse the pattern-mapping markdown table from Microsoft Learn."""
    controls: dict[str, dict[str, list[str]]] = {}
    for line in markdown.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        if line.startswith("| ---"):
            continue
        if "Control Type" in line and "Supported" in line:
            continue

        cols = [c.strip() for c in line.split("|")]
        # Leading/trailing pipe → ['', 'Button', 'None', ... , '']
        if len(cols) < 6:
            continue
        role = _normalize_control_type(cols[1])
        if not role:
            continue
        controls[role] = {
            "must": _parse_pattern_cell(cols[2]),
            "conditional": _parse_pattern_cell(cols[3]),
            "not": _parse_pattern_cell(cols[4]),
        }
    return controls


def load_patterns_reference(path: Optional[Path] = None) -> dict[str, Any]:
    ref_path = path or _REFERENCE_PATH
    data = json.loads(ref_path.read_text(encoding="utf-8"))
    controls = data.get("controls") or {}
    return {
        "schema_version": data.get("schema_version", 1),
        "source_url": data.get("source_url", _MS_PATTERN_URL),
        "source_note": data.get("source_note", ""),
        "controls": controls,
    }


def load_control_map_raw(path: Optional[Path] = None) -> dict[str, Any]:
    map_path = path or _MAP_PATH
    return json.loads(map_path.read_text(encoding="utf-8"))


def official_ms_control_types(reference: Optional[dict[str, Any]] = None) -> frozenset[str]:
    ref = reference or load_patterns_reference()
    return frozenset((ref.get("controls") or {}).keys())


def _patterns_equal(a: dict, b: dict) -> bool:
    for key in ("must", "conditional", "not"):
        if sorted(a.get(key) or []) != sorted(b.get(key) or []):
            return False
    return True


def compare_maps(
    map_data: dict[str, Any],
    reference: dict[str, Any],
    allowed_extras: frozenset[str],
) -> SyncReport:
    map_controls = map_data.get("controls") or {}
    ref_controls = reference.get("controls") or {}
    ref_keys = set(ref_controls.keys())
    map_keys = set(map_controls.keys())

    report = SyncReport(
        missing_in_map=sorted(ref_keys - map_keys),
        extra_in_map=sorted(map_keys - ref_keys - allowed_extras),
    )

    for role in sorted(ref_keys & map_keys):
        ref_pms = (ref_controls[role] or {}).get("patterns_ms") or _EMPTY_PATTERNS_MS
        map_pms = (map_controls[role] or {}).get("patterns_ms") or {}
        if not _patterns_equal(ref_pms, map_pms):
            report.patterns_drift[role] = (ref_pms, map_pms)

    return report


def stub_control_entry(role: str, patterns_ms: dict[str, Any]) -> dict[str, Any]:
    """Generic AwdUI stub for a newly discovered MS control type."""
    if role in ("Separator", "TitleBar"):
        return {"patterns_ms": patterns_ms, "read": [], "act": [], "fallback": []}

    slug = re.sub(r"[^a-z0-9]+", "_", role.lower()).strip("_")
    return {
        "patterns_ms": patterns_ms,
        "read": ["spy_inspect", "discover_control_interaction"],
        "act": [
            {
                "id": f"map_{slug}_stub",
                "tools": ["discover_control_interaction"],
                "patterns": [],
                "steps": [
                    f"TODO: curate MCP strategies for {role} (auto-sync stub; review read/act/fallback)"
                ],
            }
        ],
        "fallback": ["click_element"],
    }


def apply_missing_controls(
    map_data: dict[str, Any],
    reference: dict[str, Any],
    roles: Optional[list[str]] = None,
) -> list[str]:
    """Add missing MS control types to map_data. Returns roles added."""
    ref_controls = reference.get("controls") or {}
    map_controls = dict(map_data.get("controls") or {})
    to_add = roles if roles is not None else sorted(set(ref_controls.keys()) - set(map_controls.keys()))

    added: list[str] = []
    for role in to_add:
        if role in map_controls:
            continue
        ref_spec = ref_controls.get(role) or {}
        patterns_ms = ref_spec.get("patterns_ms") or _EMPTY_PATTERNS_MS
        map_controls[role] = stub_control_entry(role, patterns_ms)
        added.append(role)

    extras = [k for k in map_controls if k not in ref_controls]
    ordered_keys = sorted(k for k in map_controls if k not in extras) + sorted(extras)
    map_data["controls"] = {k: map_controls[k] for k in ordered_keys}
    return added


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fetch_ms_pattern_reference(
    url: str = _MS_PATTERN_URL,
    preserve_manual: bool = True,
    existing: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Fetch Microsoft Learn page and build a patterns reference document."""
    req = urllib.request.Request(url, headers={"User-Agent": "AwdUI-MCP-sync/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8", errors="replace")

    parsed = parse_ms_pattern_table(body)
    base = existing or load_patterns_reference()
    merged_controls = dict(base.get("controls") or {})

    for role, patterns in parsed.items():
        merged_controls[role] = {"patterns_ms": patterns}

    if preserve_manual:
        for role in _MANUAL_REFERENCE_TYPES:
            if role in merged_controls:
                continue
            manual = (base.get("controls") or {}).get(role)
            if manual:
                merged_controls[role] = manual

    return {
        "schema_version": base.get("schema_version", 1),
        "source_url": url,
        "source_note": (
            "Microsoft UIA pattern mapping only. Refresh: "
            "python scripts/sync_uia_control_map.py --fetch-reference"
        ),
        "controls": {k: merged_controls[k] for k in sorted(merged_controls.keys())},
    }


def format_report(report: SyncReport, reference: dict[str, Any], map_data: dict[str, Any]) -> str:
    ref_n = len(reference.get("controls") or {})
    map_n = len(map_data.get("controls") or {})
    lines = [
        f"MS reference: {ref_n} control types",
        f"AwdUI map:    {map_n} control types (+ extras allowed: Custom)",
    ]

    if report.missing_in_map:
        lines.append(f"\nMissing in uia_control_map.json ({len(report.missing_in_map)}):")
        for role in report.missing_in_map:
            lines.append(f"  - {role}")
        lines.append("  -> run: python scripts/sync_uia_control_map.py --apply")

    if report.extra_in_map:
        lines.append(f"\nUnknown in map (not MS official, not allowed extra) ({len(report.extra_in_map)}):")
        for role in report.extra_in_map:
            lines.append(f"  - {role}")

    if report.patterns_drift:
        lines.append(f"\npatterns_ms drift vs reference ({len(report.patterns_drift)}):")
        for role, (ref_pms, map_pms) in sorted(report.patterns_drift.items()):
            lines.append(f"  - {role}: map={map_pms} reference={ref_pms}")
        lines.append("  -> review manually or refresh reference with --fetch-reference")

    if not report.missing_in_map and not report.extra_in_map and not report.patterns_drift:
        lines.append("\nIn sync - no action needed.")

    return "\n".join(lines)

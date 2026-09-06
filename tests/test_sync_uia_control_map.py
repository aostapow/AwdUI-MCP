"""Tests for MS UIA map sync (check/apply, parser)."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SERVER_DIR = REPO / "mcp-servers" / "awdui-server"
SYNC_SCRIPT = REPO / "scripts" / "sync_uia_control_map.py"
MAP_PATH = SERVER_DIR / "detection" / "data" / "uia_control_map.json"
REFERENCE_PATH = SERVER_DIR / "detection" / "data" / "ms_uia_patterns_reference.json"

MS_TABLE_SNIPPET = """
| Control Type | Supported | Conditional Support | Not Supported |
| --- | --- | --- | --- |
| Button | None | Invoke, Toggle, Expand Collapse | None |
| Check Box | Toggle | None | None |
| Split Button | Invoke, Expand Collapse | None | None |
"""


@pytest.fixture
def sync_module():
    sys.path.insert(0, str(SERVER_DIR))
    from detection import ms_uia_sync

    return ms_uia_sync


def test_parse_ms_pattern_table(sync_module):
    parsed = sync_module.parse_ms_pattern_table(MS_TABLE_SNIPPET)
    assert parsed["Button"] == {
        "must": [],
        "conditional": ["Invoke", "Toggle", "ExpandCollapse"],
        "not": [],
    }
    assert parsed["CheckBox"]["must"] == ["Toggle"]
    assert parsed["SplitButton"]["must"] == ["Invoke", "ExpandCollapse"]


def test_compare_in_sync_on_repo_files(sync_module):
    reference = sync_module.load_patterns_reference(REFERENCE_PATH)
    map_data = sync_module.load_control_map_raw(MAP_PATH)
    from detection.uia_control_map import ALLOWED_EXTRA_CONTROL_TYPES

    report = sync_module.compare_maps(map_data, reference, ALLOWED_EXTRA_CONTROL_TYPES)
    assert report.missing_in_map == []
    assert report.extra_in_map == []
    assert report.patterns_drift == {}


def test_apply_adds_missing_stub_only(sync_module):
    reference = sync_module.load_patterns_reference(REFERENCE_PATH)
    map_data = json.loads(json.dumps(sync_module.load_control_map_raw(MAP_PATH)))
    controls = dict(map_data["controls"])
    removed = "Thumb"
    del controls[removed]
    map_data["controls"] = controls

    report = sync_module.compare_maps(
        map_data,
        reference,
        frozenset({"Custom"}),
    )
    assert report.missing_in_map == [removed]

    added = sync_module.apply_missing_controls(map_data, reference)
    assert added == [removed]
    assert removed in map_data["controls"]
    assert map_data["controls"][removed]["read"] == ["spy_inspect", "discover_control_interaction"]
    # Original curated entry untouched for other types
    assert map_data["controls"]["Button"]["act"][0]["id"] == "map_invoke"


def test_stub_separator_empty(sync_module):
    entry = sync_module.stub_control_entry("Separator", {"must": [], "conditional": [], "not": []})
    assert entry["read"] == []
    assert entry["act"] == []
    assert entry["fallback"] == []


def test_sync_check_script_exit_zero():
    result = subprocess.run(
        [sys.executable, str(SYNC_SCRIPT), "--check"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "In sync" in result.stdout


def test_fetch_reference_preserves_manual_types(sync_module):
    existing = sync_module.load_patterns_reference(REFERENCE_PATH)
    ref = sync_module.fetch_ms_pattern_reference(existing=existing)
    for role in ("AppBar", "SemanticZoom"):
        assert role in ref["controls"]
    assert "Button" in ref["controls"]

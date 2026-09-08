"""Tests for flows.json validation."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_flows import validate_flows  # noqa: E402


def test_valid_flow_tree():
    data = {
        "flows": [
            {
                "id": "F-01",
                "kind": "entry",
                "status": "met",
                "subtree_discovered": True,
                "source": "seed",
            },
            {
                "id": "F-02",
                "kind": "action",
                "status": "pending",
                "parent_id": "F-01",
                "source": "discovered",
            },
        ]
    }
    assert validate_flows(data) == ([], [])


def test_duplicate_id_fails():
    data = {
        "flows": [
            {"id": "F-01", "kind": "entry", "status": "pending", "subtree_discovered": False},
            {"id": "F-01", "kind": "action", "status": "pending", "parent_id": "F-01"},
        ]
    }
    errors, _warnings = validate_flows(data)
    assert any("duplicate" in e for e in errors)


def test_action_before_parent_met_warns():
    data = {
        "flows": [
            {
                "id": "F-01",
                "kind": "entry",
                "status": "pending",
                "subtree_discovered": False,
            },
            {
                "id": "F-02",
                "kind": "action",
                "status": "pending",
                "parent_id": "F-01",
                "source": "discovered",
            },
        ]
    }
    errors, warnings = validate_flows(data)
    assert not errors
    assert any("parent F-01" in w for w in warnings)


def test_action_met_before_parent_met_errors():
    data = {
        "flows": [
            {
                "id": "F-01",
                "kind": "entry",
                "status": "pending",
                "subtree_discovered": False,
            },
            {
                "id": "F-02",
                "kind": "action",
                "status": "met",
                "parent_id": "F-01",
                "source": "discovered",
            },
        ]
    }
    errors, warnings = validate_flows(data)
    assert any("parent F-01" in e for e in errors)
    assert not warnings

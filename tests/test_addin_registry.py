"""Tests for addin registry."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"))


@pytest.fixture
def mock_mcp():
    mcp = mock.MagicMock()
    tools: list = []

    def tool_decorator():
        def wrapper(fn):
            tools.append(fn.__name__)
            return fn
        return wrapper

    mcp.tool = tool_decorator
    mcp._tools = tools
    return mcp


class TestAddinRegistry:
    def test_discover_cen_manifest(self):
        from addin_sdk.registry import discover_manifests

        repo = Path(__file__).resolve().parents[1]
        manifests = discover_manifests([repo / "addins"])
        ids = {m.parent.name for m in manifests}
        assert "cen" in ids

    def test_cen_disabled_by_default(self, mock_mcp, tmp_path, monkeypatch):
        from addin_sdk.registry import bootstrap_addins

        cfg = {
            "schema_version": 1,
            "addin_paths": [str(Path(__file__).resolve().parents[1] / "addins")],
            "addins": {"cen": {"enabled": False}},
        }
        cfg_path = tmp_path / "addins.json"
        cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
        monkeypatch.setattr("addin_sdk.registry._default_config", lambda: cfg)

        registry = bootstrap_addins(mock_mcp)
        assert registry.loaded_ids() == []
        assert registry.tool_count == 0

    def test_cen_loads_when_enabled(self, mock_mcp, tmp_path, monkeypatch):
        from addin_sdk.registry import bootstrap_addins

        cfg = {
            "schema_version": 1,
            "addin_paths": [str(Path(__file__).resolve().parents[1] / "addins")],
            "addins": {"cen": {"enabled": True}},
        }
        monkeypatch.setattr("addin_sdk.registry._default_config", lambda: cfg)

        registry = bootstrap_addins(mock_mcp)
        assert "cen" in registry.loaded_ids()
        assert registry.tool_count >= 48
        assert "cen_read_grid" in mock_mcp._tools

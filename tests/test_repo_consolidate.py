"""Tests for repository consolidation."""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"),
)


@pytest.fixture
def repo_db(tmp_path, monkeypatch):
    from detection import repo_store

    db = tmp_path / "test.db"
    assets = tmp_path / "assets"
    legacy = tmp_path / "legacy_json"
    legacy.mkdir()
    monkeypatch.setattr(repo_store, "_DB_PATH", db)
    monkeypatch.setattr(repo_store, "_ASSETS_DIR", assets)
    monkeypatch.setattr(repo_store, "_LEGACY_JSON_DIR", legacy)
    monkeypatch.setattr(repo_store, "_LEGACY_JSON_BAK", tmp_path / "bak")
    repo_store.reset_migration_flag()
    repo_store.init_db(db)
    return repo_store


class TestRepoConsolidate:
    def test_merges_application_frame_host_into_calculator(self, repo_db):
        ident = {
            "mandatory": {"automation_id": "num6Button"},
            "assistive": {"name": "Seis"},
            "smart": {},
            "ordinal": {},
        }
        repo_db.upsert(
            "ApplicationFrameHost.exe",
            "",
            "Calculadora/num6Button",
            obj_class="SwfButton",
            identification=ident,
            element={"name": "Seis", "role": "Button", "automation_id": "num6Button"},
        )
        repo_db.upsert(
            "foreground",
            "",
            "Notepad/File",
            obj_class="SwfMenuItem",
            identification={"mandatory": {"name": "File"}, "assistive": {}, "smart": {}, "ordinal": {}},
        )

        from detection.repo_consolidate import consolidate_repositories

        result = consolidate_repositories()
        assert result["moved"] >= 2

        apps = {a["app_name"]: a for a in repo_db.list_applications()}
        assert "ApplicationFrameHost.exe" not in apps
        assert "foreground" not in apps
        assert "CalculatorApp.exe" in apps
        assert "Notepad.exe" in apps
        assert repo_db.get_object_by_path("Calculadora/num6Button") is not None
        assert repo_db.get_object_by_path("Notepad/File") is not None

    def test_collapses_junk_apps(self, repo_db):
        ident = {
            "mandatory": {"automation_id": "btnOk"},
            "assistive": {},
            "smart": {},
            "ordinal": {},
        }
        repo_db.upsert(
            "foreground",
            "",
            "Dialog/btnOk",
            obj_class="SwfButton",
            identification=ident,
        )
        repo_db.upsert(
            "ApplicationFrameHost.exe",
            "",
            "Dialog/btnCancel",
            obj_class="SwfButton",
            identification={"mandatory": {"automation_id": "btnCancel"}, "assistive": {}, "smart": {}, "ordinal": {}},
        )

        from detection.repo_consolidate import consolidate_repositories

        result = consolidate_repositories()
        assert result["moved"] >= 2
        apps = repo_db.list_applications()
        assert len(apps) == 1
        assert apps[0]["app_name"] == "Dialog"

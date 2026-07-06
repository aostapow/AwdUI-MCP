"""Tests for SQLite object repository store."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"))


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


class TestRepoStore:
    def test_upsert_and_get(self, repo_db):
        repo_db.upsert(
            "CalculatorApp.exe",
            "C:\\Calc.exe",
            "Calculadora/num6Button",
            obj_class="SwfButton",
            identification={
                "mandatory": {"automation_id": "num6Button"},
                "assistive": {"name": "Seis", "role": "Button"},
                "smart": {},
                "ordinal": {},
            },
            element={
                "name": "Seis",
                "role": "Button",
                "automation_id": "num6Button",
                "x": 10,
                "y": 20,
                "width": 96,
                "height": 63,
            },
        )
        obj = repo_db.get_object_by_path("Calculadora/num6Button")
        assert obj is not None
        assert obj["class"] == "SwfButton"
        assert obj["identification"]["mandatory"]["automation_id"] == "num6Button"

    def test_agent_hints(self, repo_db):
        repo_db.upsert(
            "App.exe",
            "",
            "main/btnOk",
            obj_class="SwfButton",
            identification={"mandatory": {"name": "OK"}, "assistive": {}, "smart": {}, "ordinal": {}},
            agent_hints="Usar automation_id cuando exista",
        )
        assert repo_db.get_agent_hints("main/btnOk") == "Usar automation_id cuando exista"
        repo_db.update_object("main/btnOk", agent_hints="Actualizado")
        assert repo_db.get_agent_hints("main/btnOk") == "Actualizado"

    def test_search(self, repo_db):
        repo_db.upsert(
            "App.exe",
            "",
            "frm/btnSave",
            obj_class="SwfButton",
            identification={"mandatory": {"automation_id": "btnSave"}, "assistive": {}, "smart": {}, "ordinal": {}},
        )
        hits = repo_db.search_objects("btnSave")
        assert len(hits) == 1
        assert hits[0]["repo_path"] == "frm/btnSave"

    def test_json_migration(self, repo_db, tmp_path):
        legacy = tmp_path / "legacy_json"
        data = {
            "app_id": "abc123",
            "app_name": "TestApp.exe",
            "framework": "win32",
            "windows": {
                "frmMain": {
                    "title_pattern": ".*Main.*",
                    "objects": {
                        "btnOk": {
                            "class": "SwfButton",
                            "parent": "",
                            "identification": {
                                "mandatory": {"automation_id": "btnOk"},
                                "assistive": {"role": "Button"},
                                "smart": {},
                            },
                        }
                    },
                }
            },
        }
        (legacy / "abc123.json").write_text(json.dumps(data), encoding="utf-8")
        result = repo_db.migrate_json_repos(force=True)
        assert result["imported"] == 1
        obj = repo_db.get_object_by_path("frmMain/btnOk")
        assert obj is not None
        assert obj["class"] == "SwfButton"

    def test_facade_list_objects(self, repo_db):
        from detection import object_repository as repo_mod
        repo_db.upsert(
            "App.exe",
            "",
            "w1/btn1",
            obj_class="SwfButton",
            identification={"mandatory": {"name": "btn1"}, "assistive": {}, "smart": {}, "ordinal": {}},
        )
        repo = repo_mod.load_repo("App.exe", "")
        items = repo_mod.list_objects(repo)
        paths = {i["repo_path"] for i in items}
        assert "w1/btn1" in paths

"""Tests for QTP/UFT-style WinForms repository layer."""
import os
import sys
from unittest import mock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"))


class TestWinformsMap:
    def test_infer_button(self):
        from detection.winforms_map import infer_swf_class, allowed_methods
        assert infer_swf_class(role="Button") == "SwfButton"
        assert infer_swf_class(class_name="System.Windows.Forms.TextBox") == "SwfEdit"
        assert "Click" in allowed_methods("SwfButton")
        assert "Set" in allowed_methods("SwfEdit")

    def test_build_identification(self):
        from detection.winforms_map import build_identification
        elem = {"name": "btnSave", "role": "Button", "automation_id": "btnSave"}
        ident = build_identification(elem, "SwfButton")
        assert ident["mandatory"]["automation_id"] == "btnSave"
        assert ident["assistive"]["role"] == "Button"

    def test_validate_method(self):
        from detection.winforms_map import validate_method
        assert validate_method("SwfEdit", "Set") is None
        assert "not supported" in validate_method("SwfLabel", "Click")


class TestObjectRepositoryNested:
    @pytest.fixture
    def repo_db(self, tmp_path, monkeypatch):
        from detection import repo_store

        db = tmp_path / "test.db"
        monkeypatch.setattr(repo_store, "_DB_PATH", db)
        monkeypatch.setattr(repo_store, "_ASSETS_DIR", tmp_path / "assets")
        monkeypatch.setattr(repo_store, "_LEGACY_JSON_DIR", tmp_path / "legacy")
        monkeypatch.setattr(repo_store, "_LEGACY_JSON_BAK", tmp_path / "bak")
        repo_store.reset_migration_flag()
        repo_store.init_db(db)
        return repo_store

    def test_parse_nested_path(self):
        from detection import object_repository as repo_mod
        window, chain = repo_mod.parse_repo_path("frmMain/tabDatos/txtNombre")
        assert window == "frmMain"
        assert chain == ["tabDatos", "txtNombre"]

    def test_upsert_nested_with_parent(self, repo_db):
        from detection import object_repository as repo_mod
        repo = repo_mod.load_repo("TestApp.exe")
        repo_mod.upsert_object(
            repo,
            "frmMain/tabDatos/txtNombre",
            obj_class="SwfEdit",
            identification={"mandatory": {"automation_id": "txtNombre"}, "assistive": {}, "smart": {}, "ordinal": {}},
        )
        obj = repo_mod.get_object(repo, "frmMain/tabDatos/txtNombre")
        assert obj["class"] == "SwfEdit"
        assert obj["parent"] == "tabDatos"

    def test_list_full_paths(self, repo_db):
        from detection import object_repository as repo_mod
        repo = repo_mod.load_repo("TestApp.exe")
        repo_mod.upsert_object(
            repo, "frmMain/tabDatos", obj_class="SwfPage",
            identification={"mandatory": {"name": "tabDatos"}, "assistive": {}, "smart": {}, "ordinal": {}},
        )
        repo_mod.upsert_object(
            repo, "frmMain/tabDatos/txtNombre", obj_class="SwfEdit",
            identification={"mandatory": {"automation_id": "txtNombre"}, "assistive": {}, "smart": {}, "ordinal": {}},
        )
        items = repo_mod.list_objects(repo)
        paths = {i["repo_path"] for i in items}
        assert "frmMain/tabDatos/txtNombre" in paths


class TestRepoResolver:
    def test_filter_by_parent(self):
        from detection.repo_resolver import _filter_by_parent
        parent = {"x": 10, "y": 10, "width": 200, "height": 200}
        inside = {"x": 50, "y": 50, "width": 20, "height": 20}
        outside = {"x": 500, "y": 500, "width": 20, "height": 20}
        result = _filter_by_parent([inside, outside], parent)
        assert result == [inside]

    def test_resolve_with_mock_orch(self, tmp_path, monkeypatch):
        from detection import object_repository as repo_mod
        from detection import repo_store
        from detection.repo_resolver import resolve_repo_object

        db = tmp_path / "test.db"
        monkeypatch.setattr(repo_store, "_DB_PATH", db)
        monkeypatch.setattr(repo_store, "_ASSETS_DIR", tmp_path / "assets")
        monkeypatch.setattr(repo_store, "_LEGACY_JSON_DIR", tmp_path / "legacy")
        monkeypatch.setattr(repo_store, "_LEGACY_JSON_BAK", tmp_path / "bak")
        repo_store.reset_migration_flag()
        repo_store.init_db(db)

        repo = repo_mod.load_repo("TestApp.exe")
        repo_mod.upsert_object(
            repo,
            "frmMain/btnSave",
            obj_class="SwfButton",
            identification={
                "mandatory": {"automation_id": "btnSave", "role": "Button"},
                "assistive": {"name": "Guardar"},
                "smart": {},
                "ordinal": {},
            },
        )
        mock_orch = mock.MagicMock()
        mock_orch.find_elements.return_value = {
            "found": True,
            "backend_used": "uia",
            "elements": [{
                "name": "Guardar",
                "role": "Button",
                "automation_id": "btnSave",
                "x": 10, "y": 20, "width": 80, "height": 24,
            }],
        }
        result = resolve_repo_object(repo, "frmMain/btnSave", mock_orch)
        assert result["found"]
        assert result["swf_class"] == "SwfButton"
        assert result["method"].startswith("repository:")


class TestRepoActionValidation:
    def test_rejects_unknown_method(self, monkeypatch):
        from tools import repo_action as ra
        monkeypatch.setattr(ra, "do_repo_resolve", lambda *a, **k: {
            "found": True,
            "element": {"name": "x", "role": "Text", "x": 0, "y": 0, "width": 1, "height": 1},
            "swf_class": "SwfLabel",
            "method": "repository:mandatory",
        })
        result = ra.do_repo_action("frmMain/lblTitle", "Click")
        assert not result["success"]
        assert "not supported" in result["error"]

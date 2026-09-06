"""Tests for repository framework detection and persistence."""
import os
import sys
from unittest import mock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"))


class TestRepoFramework:
    def test_merge_framework_prefers_known(self):
        from detection.repo_framework import merge_framework

        assert merge_framework("winforms", "unknown") == "winforms"
        assert merge_framework("unknown", "winforms") == "winforms"
        assert merge_framework("wpf", "winforms") == "winforms"

    def test_upsert_does_not_downgrade_framework(self, tmp_path, monkeypatch):
        from detection import repo_store

        db = tmp_path / "test.db"
        monkeypatch.setattr(repo_store, "_DB_PATH", db)
        monkeypatch.setattr(repo_store, "_ASSETS_DIR", tmp_path / "assets")
        monkeypatch.setattr(repo_store, "_LEGACY_JSON_DIR", tmp_path / "legacy")
        monkeypatch.setattr(repo_store, "_LEGACY_JSON_BAK", tmp_path / "bak")
        repo_store.reset_migration_flag()
        repo_store.init_db(db)

        repo_store.upsert(
            "Administrador.exe",
            "C:\\AST\\Administrador.exe",
            "AST/btnGuardar",
            framework="winforms",
            identification={"mandatory": {"automation_id": "btnGuardar"}, "assistive": {}, "smart": {}, "ordinal": {}},
        )
        repo_store.upsert(
            "Administrador.exe",
            "C:\\AST\\Administrador.exe",
            "AST/cboActividad",
            framework="unknown",
            identification={"mandatory": {"automation_id": "cboActividad"}, "assistive": {}, "smart": {}, "ordinal": {}},
        )
        app = repo_store.list_applications()[0]
        assert app["framework"] == "winforms"

    def test_refresh_app_framework_updates_unknown(self, tmp_path, monkeypatch):
        from detection import repo_store
        from detection.repo_framework import refresh_app_framework

        db = tmp_path / "test.db"
        monkeypatch.setattr(repo_store, "_DB_PATH", db)
        monkeypatch.setattr(repo_store, "_ASSETS_DIR", tmp_path / "assets")
        monkeypatch.setattr(repo_store, "_LEGACY_JSON_DIR", tmp_path / "legacy")
        monkeypatch.setattr(repo_store, "_LEGACY_JSON_BAK", tmp_path / "bak")
        repo_store.reset_migration_flag()
        repo_store.init_db(db)

        repo_store.upsert(
            "Administrador.exe",
            "C:\\AST\\Administrador.exe",
            "AST/btnGuardar",
            identification={"mandatory": {"automation_id": "btnGuardar"}, "assistive": {}, "smart": {}, "ordinal": {}},
        )
        app_id = repo_store.list_applications()[0]["app_id"]

        with mock.patch(
            "detection.repo_framework.guess_window_title_for_app",
            return_value="AST - Activities Manager",
        ), mock.patch(
            "detection.repo_framework.detect_framework_label",
            return_value="winforms",
        ):
            result = refresh_app_framework(app_id)

        assert result["success"] is True
        assert result["framework"] == "winforms"
        detail = repo_store.get_application(app_id)
        assert detail["framework"] == "winforms"

    def test_guess_window_title_prefers_process_match(self):
        from detection.repo_framework import guess_window_title_for_app

        app = {
            "app_id": "abc",
            "app_name": "Administrador.exe",
            "exe_path": r"C:\AST\Administrador.exe",
        }
        windows = [
            {
                "title": "Administrador: powershell.exe ...",
                "process_name": "powershell.exe",
            },
            {
                "title": "AST - Activities Manager",
                "process_name": "Administrador.exe",
            },
        ]
        conn = mock.Mock()
        conn.execute.return_value.fetchall.return_value = [{"window_key": "AST"}]
        with mock.patch("tools.windows.do_list_windows", return_value=windows):
            title = guess_window_title_for_app(app, conn=conn)
        assert title == "AST - Activities Manager"

    def test_auto_repo_persists_detected_framework(self, tmp_path, monkeypatch):
        from detection import object_repository as repo_mod
        from detection import repo_store
        from detection.auto_repo import maybe_remember_element

        db = tmp_path / "test.db"
        monkeypatch.setattr(repo_store, "_DB_PATH", db)
        monkeypatch.setattr(repo_store, "_ASSETS_DIR", tmp_path / "assets")
        monkeypatch.setattr(repo_store, "_LEGACY_JSON_DIR", tmp_path / "legacy")
        monkeypatch.setattr(repo_store, "_LEGACY_JSON_BAK", tmp_path / "bak")
        repo_store.reset_migration_flag()
        repo_store.init_db(db)

        monkeypatch.setattr(
            "tools.framework_detect.do_detect_framework",
            lambda _wt: {
                "framework": "winforms",
                "process_name": "Administrador.exe",
                "exe_path": "C:\\AST\\Administrador.exe",
            },
        )
        monkeypatch.setattr("tools.target_window.get_target", lambda: "AST - Activities Manager")
        elem = {
            "name": "Guardar",
            "role": "Button",
            "automation_id": "btnGuardar",
            "x": 10,
            "y": 20,
            "width": 40,
            "height": 30,
        }
        maybe_remember_element(elem, window_title="AST - Activities Manager")
        apps = repo_store.list_applications()
        assert apps[0]["framework"] == "winforms"

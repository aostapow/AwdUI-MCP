"""Tests for auto repository capture."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"))


class TestAutoRepo:
    def test_auto_repo_path_prefers_automation_id(self):
        from detection.auto_repo import auto_repo_path
        path = auto_repo_path(
            "Calculadora",
            {"name": "Seis", "automation_id": "num6Button", "role": "Button"},
        )
        assert path == "Calculadora/num6Button"

    def test_auto_repo_path_uses_name(self):
        from detection.auto_repo import auto_repo_path
        path = auto_repo_path("Bloc de notas", {"name": "Editor de texto", "role": "Edit"})
        assert path == "Bloc_de_notas/Editor_de_texto"

    def test_should_auto_remember_requires_target(self):
        from detection.auto_repo import should_auto_remember

        assert should_auto_remember("Calculadora", "CalculatorApp.exe") is False

    def test_should_auto_remember_with_matching_target(self, monkeypatch):
        from detection.auto_repo import should_auto_remember

        monkeypatch.setattr("tools.target_window.get_target", lambda: "Calculadora")
        assert should_auto_remember("Calculadora", "CalculatorApp.exe") is True

    def test_should_auto_remember_target_set_empty_window_title(self, monkeypatch):
        from detection.auto_repo import should_auto_remember

        monkeypatch.setattr("tools.target_window.get_target", lambda: "Calculadora")
        assert should_auto_remember(None, "CalculatorApp.exe") is True
        assert should_auto_remember("", "CalculatorApp.exe") is True

    def test_blocked_host_app(self, monkeypatch):
        from detection.auto_repo import should_auto_remember

        monkeypatch.setattr("tools.target_window.get_target", lambda: "Cursor")
        assert should_auto_remember("Cursor", "Cursor.exe", r"C:\cursor\Cursor.exe") is False

    def test_explorer_allowed_with_matching_target(self, monkeypatch):
        from detection.auto_repo import should_auto_remember

        monkeypatch.setattr(
            "tools.target_window.get_target",
            lambda: "awdui-lab-escritorio-2026-09-10",
        )
        assert should_auto_remember(
            "awdui-lab-escritorio-2026-09-10",
            "explorer.exe",
            r"C:\Windows\explorer.exe",
        ) is True

    def test_maybe_remember_element(self, tmp_path, monkeypatch):
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

        monkeypatch.setattr("tools.target_window.get_target", lambda: "Calculadora")
        monkeypatch.setattr(
            "tools.framework_detect.do_detect_framework",
            lambda _wt: {"process_name": "CalculatorApp.exe", "exe_path": "C:\\Calc.exe"},
        )
        elem = {
            "name": "Seis",
            "role": "Button",
            "automation_id": "num6Button",
            "x": 10,
            "y": 20,
            "width": 40,
            "height": 30,
        }
        path = maybe_remember_element(elem, window_title="Calculadora")
        assert path == "Calculadora/num6Button"
        repo = repo_mod.load_repo("CalculatorApp.exe", "C:\\Calc.exe")
        obj = repo_mod.get_object(repo, path)
        assert obj is not None
        assert obj["class"] == "SwfButton"

    def test_maybe_remember_skipped_without_target(self, tmp_path, monkeypatch):
        from detection import repo_store
        from detection.auto_repo import maybe_remember_element

        db = tmp_path / "test.db"
        monkeypatch.setattr(repo_store, "_DB_PATH", db)
        monkeypatch.setattr(repo_store, "_ASSETS_DIR", tmp_path / "assets")
        monkeypatch.setattr(repo_store, "_LEGACY_JSON_DIR", tmp_path / "legacy")
        monkeypatch.setattr(repo_store, "_LEGACY_JSON_BAK", tmp_path / "bak")
        repo_store.reset_migration_flag()
        repo_store.init_db(db)
        monkeypatch.setattr("tools.target_window.get_target", lambda: None)
        monkeypatch.setattr(
            "tools.framework_detect.do_detect_framework",
            lambda _wt: {"process_name": "CalculatorApp.exe", "exe_path": "C:\\Calc.exe"},
        )
        elem = {"name": "Seis", "role": "Button", "automation_id": "num6Button"}
        assert maybe_remember_element(elem, window_title="Calculadora") is None

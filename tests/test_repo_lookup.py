"""Tests for automatic repository path lookup."""
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


class TestRepoLookupScoring:
    def test_digit_name_matches_num_button(self):
        from detection.repo_lookup import find_best_repo_path, score_repo_object

        obj = {
            "repo_path": "Calculadora/num6Button",
            "logical_name": "Seis",
            "automation_id": "num6Button",
            "identification": {
                "mandatory": {"automation_id": "num6Button"},
                "assistive": {"name": "Seis", "role": "Button"},
                "smart": {},
            },
        }
        assert score_repo_object(obj, name="6", window_title="Calculadora") >= 800
        assert score_repo_object(obj, automation_id="num6Button", window_title="Calculadora") >= 1000

        repo = {"app_name": "NonExistentApp.exe", "app_id": "empty", "windows": {}}
        path = find_best_repo_path(repo, name="6", window_title="Calculadora")
        assert path is None

    def test_find_best_in_repo(self, repo_db):
        from detection import object_repository as repo_mod
        from detection.repo_lookup import find_best_repo_path

        repo = repo_mod.load_repo("CalculatorApp.exe")
        repo_mod.upsert_object(
            repo,
            "Calculadora/num1Button",
            obj_class="SwfButton",
            identification={
                "mandatory": {"automation_id": "num1Button"},
                "assistive": {"name": "Uno", "role": "Button"},
                "smart": {},
                "ordinal": {},
            },
            element={"name": "Uno", "role": "Button", "automation_id": "num1Button"},
        )
        repo_mod.upsert_object(
            repo,
            "Calculadora/num5Button",
            obj_class="SwfButton",
            identification={
                "mandatory": {"automation_id": "num5Button"},
                "assistive": {"name": "Cinco", "role": "Button"},
                "smart": {},
                "ordinal": {},
            },
            element={"name": "Cinco", "role": "Button", "automation_id": "num5Button"},
        )

        assert find_best_repo_path(repo, name="1", window_title="Calculadora") == "Calculadora/num1Button"
        assert find_best_repo_path(repo, automation_id="num5Button", window_title="Calculadora") == "Calculadora/num5Button"
        assert find_best_repo_path(repo, name="Uno", window_title="Calculadora") == "Calculadora/num1Button"


class TestLayeredRepoAutoLookup:
    def test_try_repo_without_explicit_path(self, repo_db, monkeypatch):
        from detection import object_repository as repo_mod
        from detection.layers.layered_detector import LayeredDetector, LocatorQuery

        repo = repo_mod.load_repo("CalculatorApp.exe")
        repo_mod.upsert_object(
            repo,
            "Calculadora/num7Button",
            obj_class="SwfButton",
            identification={
                "mandatory": {"automation_id": "num7Button"},
                "assistive": {"name": "Siete", "role": "Button"},
                "smart": {},
                "ordinal": {},
            },
        )

        class FakeOrch:
            def find_elements(self, **kwargs):
                return {"found": True, "elements": [{"name": "Siete", "x": 1, "y": 2, "width": 3, "height": 4}]}

        det = LayeredDetector(FakeOrch())
        monkeypatch.setattr(
            det,
            "_app_context",
            lambda _wt: ("CalculatorApp.exe", repo),
        )
        monkeypatch.setattr(
            "detection.repo_resolver.resolve_repo_object",
            lambda *_a, **_k: {
                "found": True,
                "method": "repository:mandatory",
                "element": {"name": "Siete", "x": 10, "y": 20, "width": 40, "height": 30, "backend_used": "uia"},
                "obj": {},
            },
        )

        result = det._try_repo(repo, LocatorQuery(name="7", window_title="Calculadora"))
        assert result is not None
        assert result.found
        assert result.repo_path == "Calculadora/num7Button"

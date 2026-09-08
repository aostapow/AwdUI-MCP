"""Tests for repo_hints_set MCP helper."""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"))


@pytest.fixture
def repo_db(tmp_path, monkeypatch):
    from detection import repo_store

    db = tmp_path / "test.db"
    monkeypatch.setattr(repo_store, "_DB_PATH", db)
    monkeypatch.setattr(repo_store, "_ASSETS_DIR", tmp_path / "assets")
    monkeypatch.setattr(repo_store, "_LEGACY_JSON_DIR", tmp_path / "legacy")
    monkeypatch.setattr(repo_store, "_LEGACY_JSON_BAK", tmp_path / "bak")
    repo_store.reset_migration_flag()
    repo_store.init_db(db)
    return repo_store


def test_do_repo_hints_set_replace_and_append(repo_db):
    from tools.repo_action import do_repo_hints_set

    repo_db.upsert(
        "App.exe",
        "",
        "main/btnOk",
        obj_class="SwfButton",
        identification={"mandatory": {"name": "OK"}, "assistive": {}, "smart": {}, "ordinal": {}},
    )
    r1 = do_repo_hints_set("main/btnOk", "verify_automation_id: display1")
    assert r1["success"] is True
    r2 = do_repo_hints_set("main/btnOk", "nota: usar click si invoke falla", append=True)
    assert r2["success"] is True
    assert r2["appended"] is True
    assert "display1" in r2["agent_hints"]
    assert "invoke falla" in r2["agent_hints"]


def test_do_repo_hints_set_missing_object(repo_db):
    from tools.repo_action import do_repo_hints_set

    r = do_repo_hints_set("missing/obj", "x")
    assert r["success"] is False


def test_do_repo_capture_with_agent_hints(repo_db, monkeypatch):
    from tools.repo_action import do_repo_capture

    def fake_find(**_kwargs):
        return {
            "found": True,
            "elements": [
                {
                    "name": "Uno",
                    "role": "Button",
                    "automation_id": "btnOne",
                    "x": 1,
                    "y": 2,
                    "width": 10,
                    "height": 10,
                }
            ],
        }

    monkeypatch.setattr("tools.ui_automation.do_find_element", fake_find)
    result = do_repo_capture(
        "Calc/btnOne",
        automation_id="btnOne",
        name="Uno",
        agent_hints="metodo_preferido: invoke_element",
    )
    assert result.get("success") is True
    assert repo_db.get_agent_hints("Calc/btnOne") == "metodo_preferido: invoke_element"

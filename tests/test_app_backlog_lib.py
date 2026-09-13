"""Tests for scripts/app_backlog_lib.py (isolated tmp paths)."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import app_backlog_lib as abl  # noqa: E402


@pytest.fixture
def backlog_env(tmp_path, monkeypatch):
    apps = tmp_path / "apps"
    state_path = tmp_path / "state.json"
    runs = tmp_path / "runs"
    apps.mkdir()
    runs.mkdir()
    state_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(abl, "APPS_ROOT", apps)
    monkeypatch.setattr(abl, "STATE_PATH", state_path)
    monkeypatch.setattr(abl, "RUNS_ROOT", runs)
    return {"apps": apps, "state": state_path, "runs": runs}


def test_slug_from_app_name():
    assert abl.slug_from_app_name("Calculadora") == "calculadora"
    assert abl.slug_from_app_name("Bloc de notas") == "bloc-de-notas"


def test_compute_progress_complete_when_all_done():
    items = [
        {"id": "W-H01", "status": "done"},
        {"id": "W-H02", "status": "na"},
    ]
    prog = abl.compute_progress(items)
    assert prog["complete"] is True
    assert prog["done"] == 1


def test_compute_progress_not_complete_with_pending():
    items = [{"id": "W-H01", "status": "pending"}]
    prog = abl.compute_progress(items)
    assert prog["complete"] is False


def test_next_pending_hygiene_priority_zero_before_one():
    backlog = {"items": list(abl.default_hygiene_items())}
    nxt = abl.next_pending_item(backlog)
    assert nxt["id"] == "W-H01"


def test_next_pending_respects_parent(backlog_env):
    backlog = {
        "items": [
            {"id": "W-F-01", "category": "flow", "status": "pending", "priority": 1, "parent_id": None},
            {
                "id": "W-F-02",
                "category": "flow",
                "status": "pending",
                "priority": 0,
                "parent_id": "W-F-01",
            },
        ]
    }
    nxt = abl.next_pending_item(backlog)
    assert nxt["id"] == "W-F-01"
    backlog["items"][0]["status"] = "done"
    nxt2 = abl.next_pending_item(backlog)
    assert nxt2["id"] == "W-F-02"


def test_mark_item_and_save_recomputes_next(backlog_env):
    slug = "test-app"
    bl = abl.create_backlog("Test App", slug=slug, run_id="test-app-2026-01-01")
    first = abl.next_pending_item(bl)
    assert first and first["id"] == "W-H01"
    abl.mark_item(bl, "W-H01", "done")
    abl.save_backlog(slug, bl)
    assert bl["next_item_id"] == "W-H02"


def test_add_discovered_items_dedupes_ref(backlog_env):
    bl = abl.create_backlog("X", slug="x", run_id="x-1")
    added = abl.add_discovered_items(
        bl,
        [{"ref": "F-99", "title": "Nuevo", "success_criteria": "ok"}],
        run_id="x-1",
    )
    assert added == 1
    added2 = abl.add_discovered_items(
        bl,
        [{"ref": "F-99", "title": "Dup"}],
        run_id="x-1",
    )
    assert added2 == 0


def test_flow_to_backlog_item_id():
    item = abl.flow_to_backlog_item(
        {"id": "F-01", "title": "Suma", "status": "met"},
        run_id="r1",
    )
    assert item["id"] == "W-F-01"
    assert item["status"] == "done"


def test_init_or_resume_creates_and_patches_state(backlog_env):
    result = abl.init_or_resume("Calculadora", run_id="calculadora-test")
    assert result["created"] is True
    assert result["app_slug"] == "calculadora"
    state = json.loads(backlog_env["state"].read_text(encoding="utf-8-sig"))
    assert state["active_lab"] == "Calculadora"
    assert state["active_app_slug"] == "calculadora"
    assert state["backlog_ref"].endswith("apps/calculadora/backlog.json")


def test_backlog_hint_for_state_missing_file():
    hint = abl.backlog_hint_for_state({"active_lab": "Foo", "active_app_slug": "foo"})
    assert "NO EXISTE" in hint


def test_backlog_hint_for_state_next_item(backlog_env):
    abl.init_or_resume("Bar", run_id="bar-1")
    hint = abl.backlog_hint_for_state({"active_lab": "Bar", "active_app_slug": "bar"})
    assert "W-H01" in hint
    assert "CANONICO" in hint

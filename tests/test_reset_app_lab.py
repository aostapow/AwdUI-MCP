"""Tests for scripts/reset_app_lab.py."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import app_backlog_lib as abl  # noqa: E402
import reset_app_lab as ral  # noqa: E402


@pytest.fixture
def reset_env(tmp_path, monkeypatch):
    apps = tmp_path / "apps"
    runs = tmp_path / "runs"
    state_path = tmp_path / "state.json"
    apps.mkdir()
    runs.mkdir()
    slug_dir = apps / "foo"
    slug_dir.mkdir()
    (slug_dir / "backlog.json").write_text("{}", encoding="utf-8")
    (runs / "foo-2026-01-01").mkdir()
    (runs / "foo-2026-01-01" / "flows.json").write_text("{}", encoding="utf-8")
    state_path.write_text(
        json.dumps(
            {
                "active_lab": "Foo",
                "lab_apps": {"Foo": {"flows_progress": {"met": 5}}},
                "calculator_perfect": True,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(abl, "APPS_ROOT", apps)
    monkeypatch.setattr(abl, "RUNS_ROOT", runs)
    monkeypatch.setattr(ral, "RUNS_ROOT", runs)
    monkeypatch.setattr(ral, "STATE_PATH", state_path)
    monkeypatch.setattr(ral, "app_dir", abl.app_dir)
    return {"state": state_path, "runs": runs, "apps": apps}


def test_reset_removes_runs_and_app_dir(reset_env):
    result = ral.reset_app_lab("Foo", dry_run=False)
    assert "foo-2026-01-01" in result["removed_run_dirs"]
    assert not (reset_env["apps"] / "foo").exists()
    assert not (reset_env["runs"] / "foo-2026-01-01").exists()
    state = json.loads(reset_env["state"].read_text(encoding="utf-8-sig"))
    assert "Foo" not in state.get("lab_apps", {})


def test_reset_dry_run_keeps_files(reset_env):
    ral.reset_app_lab("Foo", dry_run=True)
    assert (reset_env["apps"] / "foo" / "backlog.json").is_file()
    assert (reset_env["runs"] / "foo-2026-01-01").is_dir()

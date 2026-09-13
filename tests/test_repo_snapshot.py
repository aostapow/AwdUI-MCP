"""Tests for repo snapshot export."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def test_match_app_calculadora_calculatorapp():
    from repo_snapshot_lib import _match_app

    assert _match_app("Calculadora", "CalculatorApp.exe") is True
    assert _match_app("Bloc de notas", "Notepad.exe") is False


def test_write_repo_snapshot_no_discovered(tmp_path):
    from repo_snapshot_lib import write_repo_snapshot

    run = tmp_path / "run"
    run.mkdir()
    assert write_repo_snapshot(run) is None


def test_build_repo_snapshot_empty_app(tmp_path, monkeypatch):
    from repo_snapshot_lib import build_repo_snapshot

    run = tmp_path / "run"
    run.mkdir()
    (run / "discovered.yaml").write_text("app_name: UnknownApp\n", encoding="utf-8")

    server = ROOT / "mcp-servers" / "awdui-server"
    sys.path.insert(0, str(server))
    from detection import repo_store

    db = tmp_path / "repo.db"
    monkeypatch.setattr(repo_store, "_DB_PATH", db)
    monkeypatch.setattr(repo_store, "_ASSETS_DIR", tmp_path / "assets")
    monkeypatch.setattr(repo_store, "_LEGACY_JSON_DIR", tmp_path / "legacy")
    monkeypatch.setattr(repo_store, "_LEGACY_JSON_BAK", tmp_path / "bak")
    repo_store.reset_migration_flag()
    repo_store.init_db(db)

    snap = build_repo_snapshot(run)
    assert snap is not None
    assert snap["object_count"] == 0

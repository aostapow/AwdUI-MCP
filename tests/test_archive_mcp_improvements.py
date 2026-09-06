"""Tests for archiving MCP improvement proposals by Estado."""
from pathlib import Path

from scripts.archive_mcp_improvements import parse_estado, run_archive


def _write(path: Path, estado: str) -> None:
    path.write_text(
        f"# Test\n\n| **Estado** | {estado} |\n",
        encoding="utf-8",
    )


def test_parse_estado_variants():
    assert parse_estado("| **Estado** | propuesta |") == "propuesta"
    assert parse_estado("| **Estado** | aplicada |") == "aplicada"
    assert parse_estado(
        "| **Estado** | aplicada (consolidada en foo) |"
    ) == "aplicada"
    assert parse_estado("| **Estado** | aceptada |") == "aceptada"
    assert parse_estado("| **Estado** | rechazada |") == "rechazada"


def test_run_archive_moves_applied_and_keeps_pending(tmp_path, monkeypatch):
    root = tmp_path / "_MCP_IMPROVEMENT"
    skill = root / "mejoras-skill"
    skill.mkdir(parents=True)
    _write(skill / "pending.md", "propuesta")
    _write(skill / "done.md", "aplicada")
    _write(skill / "reject.md", "rechazada")

    monkeypatch.setattr("scripts.archive_mcp_improvements.IMPROVEMENT_ROOT", root)
    monkeypatch.setattr("scripts.archive_mcp_improvements.REPO_ROOT", tmp_path)

    result = run_archive(dry_run=False)
    assert result["archived"] == 2
    assert (skill / "pending.md").is_file()
    assert not (skill / "done.md").is_file()
    assert (root / "aceptadas" / "mejoras-skill" / "done.md").is_file()
    assert (root / "rechazadas" / "mejoras-skill" / "reject.md").is_file()

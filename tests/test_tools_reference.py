"""Tests for MCP tools reference validation script."""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "validate_tools_reference.py"


def test_tools_reference_in_sync():
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout

    audit = REPO / "scripts" / "audit_catalog_vs_code.py"
    result2 = subprocess.run(
        [sys.executable, str(audit)],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert result2.returncode == 0, result2.stderr or result2.stdout

"""CI test: uia_control_map.json stays complete vs Microsoft control types."""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "validate_uia_control_map.py"


def test_uia_control_map_validation_script():
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_validate_control_map_in_process():
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"))
    from detection.uia_control_map import OFFICIAL_MS_CONTROL_TYPES, validate_control_map

    errors = validate_control_map()
    assert errors == []
    assert len(OFFICIAL_MS_CONTROL_TYPES) == 40

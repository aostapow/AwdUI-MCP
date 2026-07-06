#!/usr/bin/env python3
"""Manual AwdUI update — download and apply latest release zip."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "mcp-servers" / "awdui-server"))

from auto_update import run_update  # noqa: E402

result = run_update(force=True)

if result.updated:
    sys.stderr.write(
        f"Update complete — v{result.latest}. "
        "Restart the MCP client (Cursor / Claude Desktop) to load the new version.\n"
    )
    sys.exit(0)

if result.reason in ("already-current", "already-applied"):
    ver = result.latest or result.current
    sys.stderr.write(f"Already up to date (v{ver}).\n")
    sys.exit(0)

sys.stderr.write(f"Update did not complete ({result.reason or 'unknown'}).\n")
if result.error:
    sys.stderr.write(f"{result.error}\n")
sys.exit(1 if result.reason in ("check-failed", "apply-failed") else 0)

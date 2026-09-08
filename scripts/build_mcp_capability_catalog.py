#!/usr/bin/env python3
"""Build lab-apps/mcp-capability-catalog.json from code + UIA control map."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lab_coverage_lib import CATALOG_PATH, write_catalog  # noqa: E402


def main() -> int:
    catalog = write_catalog(CATALOG_PATH)
    n_tools = catalog["mcp_tools"]["total"]
    n_ctrl = catalog["uia_controls"]["total"]
    n_bind = catalog["act_bindings"]["total"]
    print(f"OK — catalog written to {CATALOG_PATH}")
    print(f"  mcp_tools: {n_tools}  uia_controls: {n_ctrl}  act_bindings: {n_bind}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

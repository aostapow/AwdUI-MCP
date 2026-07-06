#!/usr/bin/env python3
"""AwdUI MCP launcher — optional auto-update, then start server.py."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER_DIR = ROOT / "mcp-servers" / "awdui-server"
sys.path.insert(0, str(SERVER_DIR))
os.chdir(ROOT)


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv(ROOT / ".env")

if sys.platform == "win32":
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

from auto_update import UPDATE_CONFIG, auto_update_enabled, run_update  # noqa: E402

if auto_update_enabled():
    try:
        result = run_update(force=False)
        if result.updated:
            sys.stderr.write(
                f"[AwdUI:launcher] Updated to v{result.latest}. "
                "Restart the MCP client if tools behave unexpectedly.\n"
            )
    except Exception as exc:
        sys.stderr.write(f"[AwdUI:launcher] Update step failed: {exc}\n")

server_entry = ROOT / UPDATE_CONFIG["server_entry"]
if not server_entry.is_file():
    sys.stderr.write(f"[AwdUI:launcher] Server entry not found: {server_entry}\n")
    sys.exit(1)

proc = subprocess.run([sys.executable, str(server_entry)], env=os.environ)
sys.exit(proc.returncode)

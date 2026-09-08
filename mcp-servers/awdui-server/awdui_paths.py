"""Runtime path helpers under AWDUI_DATA (~/.awdui-mcp by default)."""
from __future__ import annotations

import os
from pathlib import Path


def data_dir() -> Path:
    root = Path(os.environ.get("AWDUI_DATA", Path.home() / ".awdui-mcp"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def diagnostics_dir() -> Path:
    path = data_dir() / "diagnostics"
    path.mkdir(parents=True, exist_ok=True)
    return path


def screenshots_dir() -> Path:
    path = data_dir() / "screenshots"
    path.mkdir(parents=True, exist_ok=True)
    return path


def user_addins_dir() -> Path:
    path = data_dir() / "addins"
    path.mkdir(parents=True, exist_ok=True)
    return path


def addins_config_path() -> Path:
    return data_dir() / "addins.json"

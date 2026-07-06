"""Pytest path setup for awdui-server imports."""
import os
import sys

_SERVER_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "mcp-servers",
    "awdui-server",
)
if _SERVER_DIR not in sys.path:
    sys.path.insert(0, _SERVER_DIR)

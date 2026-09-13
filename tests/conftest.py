"""Pytest path setup for awdui-server imports."""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SERVER_DIR = os.path.join(_ROOT, "mcp-servers", "awdui-server")
_SCRIPTS_DIR = os.path.join(_ROOT, "scripts")
if _SERVER_DIR not in sys.path:
    sys.path.insert(0, _SERVER_DIR)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

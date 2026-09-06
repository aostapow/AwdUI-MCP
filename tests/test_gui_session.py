"""Tests for supervised GUI session guard."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "mcp-servers" / "awdui-server"
sys.path.insert(0, str(SERVER))
sys.path.insert(0, str(ROOT))


def test_require_supervised_session_blocks_without_env():
    from tests.integration.gui_session import require_supervised_session

    env = os.environ.copy()
    env.pop("AWDUI_GUI_SESSION", None)
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(SystemExit) as exc:
            require_supervised_session("test_script")
        assert exc.value.code == 2


def test_coordinate_click_blocked_outside_mcp_and_session():
    from tools.input_tools import do_click

    env = os.environ.copy()
    env.pop("AWDUI_MCP_SERVER", None)
    env.pop("AWDUI_GUI_SESSION", None)
    env.pop("PYTEST_CURRENT_TEST", None)
    with patch.dict(os.environ, env, clear=True):
        result = do_click(100, 100)
    assert result.get("success") is False
    assert "BLOCKED" in (result.get("error") or "")


def test_guarded_click_aborts_when_window_gone():
    from tests.integration import gui_session

    gui_session.clear_lock()
    gui_session._state.clear()
    os.environ["AWDUI_GUI_SESSION"] = "test"
    gui_session.begin(name="test", window_title="Calculadora", max_clicks=5)

    with patch.object(gui_session, "calculator_window_alive", return_value=False):
        with pytest.raises(RuntimeError, match="no longer open"):
            gui_session.guarded_click(10, 10, window_title="Calculadora", reason="test")

    gui_session.end()

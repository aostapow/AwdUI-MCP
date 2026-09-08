"""Tests for smart app launch (reuse / replace)."""
from __future__ import annotations

from unittest import mock

from tools.app_launch import (
    attach_uwp_shell_siblings,
    collect_primary_pids,
    launch_key,
    match_app_windows,
    pick_primary_window,
    rank_app_window,
)


class TestLaunchKey:
    def test_calc_exe(self):
        assert launch_key("calc.exe") == "calc"
        assert launch_key(r"C:\Windows\System32\calc.exe") == "calc"


class TestMatchAppWindows:
    def _uwp_windows(self):
        return [
            {
                "title": "Calculadora",
                "process_name": "CalculatorApp.exe",
                "hwnd": 100,
                "width": 400,
                "height": 600,
            },
            {
                "title": "Calculadora",
                "process_name": "ApplicationFrameHost.exe",
                "hwnd": 101,
                "width": 420,
                "height": 640,
            },
            {"title": "Notepad", "process_name": "notepad.exe", "hwnd": 200, "width": 300, "height": 200},
        ]

    def test_matches_uwp_core_by_process_substring(self):
        matches = match_app_windows(self._uwp_windows(), "calc.exe")
        assert len(matches) == 2

    def test_generic_notepad_match(self):
        windows = [
            {"title": "Untitled - Notepad", "process_name": "notepad.exe", "hwnd": 1, "width": 100, "height": 100},
        ]
        matches = match_app_windows(windows, "notepad.exe")
        assert len(matches) == 1

    def test_pick_prefers_core_over_uwp_shell(self):
        matches = match_app_windows(self._uwp_windows(), "calc.exe")
        primary = pick_primary_window(matches)
        assert primary["process_name"] == "CalculatorApp.exe"

    def test_rank_scores_core_higher_than_shell(self):
        calc = {"process_name": "CalculatorApp.exe", "width": 100, "height": 100}
        shell = {"process_name": "ApplicationFrameHost.exe", "width": 500, "height": 500}
        assert rank_app_window(calc) > rank_app_window(shell)

    def test_attach_uwp_shell_siblings(self):
        windows = self._uwp_windows()
        core = [windows[0]]
        attached = attach_uwp_shell_siblings(windows, core)
        assert len(attached) == 2


class TestDoLaunchAppReuse:
    @mock.patch("tools.windows.subprocess.Popen")
    @mock.patch("tools.app_launch.try_reuse_existing")
    def test_reuses_without_spawn(self, mock_reuse, mock_popen):
        from tools.windows import do_launch_app

        mock_reuse.return_value = {
            "success": True,
            "pid": 4242,
            "reused": True,
            "window_title": "Calculadora",
            "closed_extra": 0,
            "action": "focused",
        }
        result = do_launch_app("calc.exe")
        assert result["reused"] is True
        assert result["pid"] == 4242
        mock_popen.assert_not_called()

    @mock.patch("tools.windows.subprocess.Popen")
    @mock.patch("tools.app_launch.try_reuse_existing")
    def test_spawn_when_no_existing(self, mock_reuse, mock_popen):
        from tools.windows import do_launch_app

        mock_reuse.return_value = None
        mock_proc = mock.MagicMock()
        mock_proc.pid = 9999
        mock_popen.return_value = mock_proc
        result = do_launch_app("calc.exe")
        assert result["success"] is True
        assert result["reused"] is False
        mock_popen.assert_called_once()

    @mock.patch("tools.windows.subprocess.Popen")
    @mock.patch("tools.app_launch.try_reuse_existing")
    def test_replace_kills_then_spawns(self, mock_reuse, mock_popen):
        from tools.windows import do_launch_app

        mock_reuse.return_value = None
        mock_proc = mock.MagicMock()
        mock_proc.pid = 1111
        mock_popen.return_value = mock_proc
        result = do_launch_app("calc.exe", replace=True)
        mock_reuse.assert_called_once_with("calc.exe", replace=True)
        assert result["reused"] is False
        mock_popen.assert_called_once()

    @mock.patch("tools.windows.subprocess.Popen")
    def test_reuse_false_always_spawns(self, mock_popen):
        from tools.windows import do_launch_app

        mock_proc = mock.MagicMock()
        mock_proc.pid = 5555
        mock_popen.return_value = mock_proc
        result = do_launch_app("notepad.exe", reuse=False)
        assert result["success"] is True
        assert result["reused"] is False
        mock_popen.assert_called_once()


class TestCloseExtras:
    @mock.patch("tools.app_launch.kill_process_pid", return_value=True)
    @mock.patch("tools.app_launch.get_window_pid")
    def test_collect_and_close_extra_pids(self, mock_pid, mock_kill):
        from tools.app_launch import close_extra_instances

        mock_pid.side_effect = lambda hwnd: {100: 1000, 101: 2000, 102: 3000}[hwnd]
        windows = [
            {"title": "Calculadora", "process_name": "CalculatorApp.exe", "hwnd": 100, "width": 400, "height": 600},
            {"title": "Calculadora", "process_name": "CalculatorApp.exe", "hwnd": 101, "width": 400, "height": 600},
            {"title": "Calculadora", "process_name": "CalculatorApp.exe", "hwnd": 102, "width": 400, "height": 600},
        ]
        keep = windows[0]
        closed = close_extra_instances(windows, keep)
        assert closed == 2
        assert mock_kill.call_count == 2

    def test_collect_primary_pids(self):
        with mock.patch("tools.app_launch.get_window_pid", return_value=42):
            pids = collect_primary_pids(
                [{"hwnd": 1, "process_name": "CalculatorApp.exe"}],
            )
        assert pids == {42}

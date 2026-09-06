"""Unit tests for HWND scope and UIA cache."""
import sys
from unittest import mock

import pytest

sys.path.insert(0, "mcp-servers/awdui-server")


class TestUiaTreeCache:
    def test_get_descendants_caches(self):
        from detection.uia_tree_cache import get_descendants, invalidate_all

        invalidate_all()
        calls = []

        def fetch():
            calls.append(1)
            return ["a", "b"]

        r1 = get_descendants(12345, fetch, scope="test")
        r2 = get_descendants(12345, fetch, scope="test")
        assert r1 == ["a", "b"]
        assert r2 == ["a", "b"]
        assert len(calls) == 1

    def test_invalidate_clears_hwnd(self):
        from detection.uia_tree_cache import get_descendants, invalidate, invalidate_all

        invalidate_all()

        def fetch():
            return [1]

        get_descendants(99, fetch, scope="s")
        invalidate(99, scope="s")
        calls = []

        def fetch2():
            calls.append(1)
            return [2]

        result = get_descendants(99, fetch2, scope="s")
        assert result == [2]
        assert calls == [1]


class TestHwndScope:
    def test_resolve_invalid_hwnd(self):
        from detection.hwnd_scope import resolve_window_from_hwnd

        result = resolve_window_from_hwnd(0)
        assert not result.get("success")

    @mock.patch("detection.hwnd_scope.validate_hwnd_in_target", return_value=(True, ""))
    @mock.patch("detection.hwnd_scope._window_from_hwnd", return_value=None)
    def test_resolve_missing_window(self, *_mocks):
        from detection.hwnd_scope import resolve_window_from_hwnd

        result = resolve_window_from_hwnd(123456)
        assert not result.get("success")
        assert "Invalid" in result.get("error", "")


class TestInvalidateTool:
    def test_do_invalidate_all(self):
        from tools.wait_tools import do_invalidate_uia_cache

        result = do_invalidate_uia_cache()
        assert result.get("success")
        assert result.get("invalidated") == "all"

    def test_do_invalidate_hwnd(self):
        from tools.wait_tools import do_invalidate_uia_cache

        result = do_invalidate_uia_cache(hwnd=42)
        assert result.get("success")
        assert result.get("hwnd") == 42


class TestListAppWindows:
    @mock.patch("tools.windows.do_list_windows")
    @mock.patch("tools.window_scope.resolve_window_scope")
    @mock.patch("tools.target_window.get_target", return_value="MyApp")
    def test_filters_by_pid(self, _gt, mock_scope, mock_list):
        from tools.windows import do_list_app_windows

        mock_scope.return_value = {"window": {"process_id": 100, "process_name": "myapp.exe"}}
        mock_list.return_value = [
            {"title": "Main", "pid": 100, "hwnd": 1},
            {"title": "Other", "pid": 200, "hwnd": 2},
        ]
        wins = do_list_app_windows()
        assert len(wins) == 1
        assert wins[0]["pid"] == 100

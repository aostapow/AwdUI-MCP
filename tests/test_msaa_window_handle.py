"""MSAA backend accepts window_handle like UIA orchestrator."""
from __future__ import annotations

from unittest import mock

import pytest


@pytest.mark.skipif(__import__("sys").platform != "win32", reason="Windows only")
class TestMSAAWindowHandle:
    def test_list_elements_accepts_window_handle_kwarg(self):
        from detection.backends.msaa_backend import MSAABackend

        backend = MSAABackend()
        fake_elem = mock.Mock(role="RadioButton", visible=True)
        with mock.patch.object(backend, "_get_tree", return_value=[fake_elem]) as tree_mock:
            out = backend.list_elements(
                window_title="Calculadora",
                max_depth=3,
                role="RadioButton",
                window_handle=12345,
            )
        tree_mock.assert_called_once_with("Calculadora", 3, window_handle=12345)
        assert out == [fake_elem]

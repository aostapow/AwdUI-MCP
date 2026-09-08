"""UIA backend menu fast path — no depth-100 role walks."""
from __future__ import annotations

import os
import sys
from unittest import mock

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"),
)


class TestMenuFastPath:
    def test_collect_descendants_menuitem_uses_shallow_cap(self):
        from detection.backends import uia_backend as mod

        window = mock.MagicMock()
        window.element_info.element = object()
        window.child_window.return_value.exists.return_value = False
        window.descendants.return_value = ["leaf"]

        with mock.patch.object(
            mod,
            "_walk_tree_comtypes",
            return_value=["a"],
        ) as walk_mock:
            backend = mod.UIABackend()
            backend._collect_descendants(window, "control", 6, "MenuItem")

        walk_mock.assert_called()
        for _args, kwargs in walk_mock.call_args_list:
            assert kwargs.get("max_depth", walk_mock.call_args[0][2]) <= 8
        depth_arg = walk_mock.call_args[0][2]
        assert depth_arg <= 8

    def test_collect_descendants_button_never_uses_depth_100(self):
        from detection.backends import uia_backend as mod

        window = mock.MagicMock()
        window.element_info.element = object()
        window.descendants.return_value = []

        with mock.patch.object(
            mod,
            "_walk_tree_comtypes",
            return_value=["node"],
        ) as walk_mock:
            backend = mod.UIABackend()
            backend._collect_descendants(window, "control", 12, "Button")

        depth_arg = walk_mock.call_args[0][2]
        assert depth_arg <= 24
        assert depth_arg != 100

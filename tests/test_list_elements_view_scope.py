"""Tests for list_elements view_scope content pane walk root."""
from __future__ import annotations

from unittest import mock

from detection.spatial_cluster import resolve_content_walk_root


class TestResolveContentWalkRoot:
    def test_picks_widest_pane_child(self):
        narrow = mock.Mock()
        narrow.element_info = mock.Mock(
            name="Nav",
            control_type="Pane",
            rectangle=mock.Mock(left=0, right=200, top=0, bottom=800),
            automation_id="nav",
            class_name="",
            framework_id="",
            process_id=1,
            handle=1,
            visible=True,
        )
        wide = mock.Mock()
        wide.element_info = mock.Mock(
            name="Content",
            control_type="Pane",
            rectangle=mock.Mock(left=200, right=1200, top=0, bottom=800),
            automation_id="content",
            class_name="",
            framework_id="",
            process_id=1,
            handle=2,
            visible=True,
        )
        root = mock.Mock()
        root.children.return_value = [narrow, wide]
        picked = resolve_content_walk_root(root)
        assert picked is wide

    def test_returns_none_when_no_children(self):
        root = mock.Mock()
        root.children.return_value = []
        assert resolve_content_walk_root(root) is None

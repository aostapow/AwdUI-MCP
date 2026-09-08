"""Tests for UIA find fast paths (direct lookup + progressive depth)."""
from __future__ import annotations

from unittest import mock

from detection.backends.uia_backend import (
    UIABackend,
    _FIND_DEPTH_LADDER,
    _FIND_DEPTH_LADDER_AUTOMATION_ID,
    _SIDEBAR_TREE_FULL_ITEMS,
    _find_raw_by_automation_id,
    _should_skip_spy_list,
)


class TestFindDepthLadder:
    def test_ladder_capped_at_24(self):
        assert max(_FIND_DEPTH_LADDER) == 24
        assert 100 not in _FIND_DEPTH_LADDER

    def test_automation_id_ladder_shallower(self):
        assert _FIND_DEPTH_LADDER_AUTOMATION_ID == (4, 8, 14)
        assert max(_FIND_DEPTH_LADDER_AUTOMATION_ID) < max(_FIND_DEPTH_LADDER)


class TestFindElementsProgressive:
    def test_stops_at_first_depth_with_match(self):
        backend = UIABackend()
        calls: list[int] = []

        def _fake_list(**kwargs):
            calls.append(int(kwargs["max_depth"]))
            depth = kwargs["max_depth"]
            from detection.element_model import DetectedElement

            if depth >= 14:
                return [
                    DetectedElement(
                        name="Chat Awamori, Nicolas",
                        role="TreeItem",
                        automation_id="menur1oc",
                    )
                ]
            return []

        with mock.patch.object(backend, "list_elements", side_effect=_fake_list), mock.patch.object(
            backend, "_try_spy_find", return_value=[]
        ), mock.patch(
            "detection.backends.uia_backend._get_desktop",
            return_value=mock.Mock(),
        ), mock.patch(
            "detection.backends.uia_backend._resolve_window",
            return_value=mock.Mock(),
        ), mock.patch(
            "detection.backends.uia_backend._find_raw_direct",
            return_value=None,
        ):
            hits = backend.find_elements(
                name="Awamori",
                role="TreeItem",
                window_title="Teams",
            )
        assert hits
        assert hits[0].automation_id == "menur1oc"
        assert calls == [6, 10, 14]

    def test_direct_find_before_list_walk(self):
        backend = UIABackend()
        wrapper = mock.Mock()
        from detection.element_model import DetectedElement

        det = DetectedElement(
            name="Chat Awamori, Nicolas",
            role="TreeItem",
            automation_id="menur1oc",
        )
        with mock.patch.object(backend, "_try_spy_find", return_value=[]), mock.patch(
            "detection.backends.uia_backend._get_desktop",
            return_value=mock.Mock(),
        ), mock.patch(
            "detection.backends.uia_backend._resolve_window",
            return_value=wrapper,
        ), mock.patch(
            "detection.backends.uia_backend._find_raw_direct",
            return_value=wrapper,
        ) as direct, mock.patch(
            "detection.backends.uia_backend._pywinauto_to_element",
            return_value=det,
        ), mock.patch.object(backend, "list_elements") as list_mock:
            hits = backend.find_elements(
                name="Chat Awamori",
                role="TreeItem",
                window_title="Teams",
            )
        direct.assert_called_once()
        list_mock.assert_not_called()
        assert hits and hits[0].automation_id == "menur1oc"

    def test_automation_id_uses_comtypes_before_child_window(self):
        window = mock.Mock()
        wrapper = mock.Mock()
        with mock.patch(
            "detection.backends.uia_backend._find_raw_by_automation_id_comtypes",
            return_value=wrapper,
        ) as comtypes_find, mock.patch(
            "detection.backends.uia_backend._pywinauto_to_element",
            return_value=mock.Mock(automation_id="num7Button", name="Siete", role="Button"),
        ):
            hit = _find_raw_by_automation_id(window, "num7Button")
        comtypes_find.assert_called_once_with(window, "num7Button")
        assert hit is wrapper

    def test_automation_id_skips_spy_and_list_when_comtypes_hits(self):
        backend = UIABackend()
        wrapper = mock.Mock()
        from detection.element_model import DetectedElement

        det = DetectedElement(
            name="Siete",
            role="Button",
            automation_id="num7Button",
        )
        with mock.patch(
            "detection.backends.uia_backend._get_desktop",
            return_value=mock.Mock(),
        ), mock.patch(
            "detection.backends.uia_backend._resolve_window",
            return_value=wrapper,
        ), mock.patch(
            "detection.backends.uia_backend._find_raw_by_automation_id",
            return_value=wrapper,
        ), mock.patch(
            "detection.backends.uia_backend._pywinauto_to_element",
            return_value=det,
        ), mock.patch.object(backend, "_try_spy_find") as spy, mock.patch.object(
            backend, "list_elements"
        ) as list_mock:
            hits = backend.find_elements(
                automation_id="num7Button",
                window_title="Calculadora",
            )
        spy.assert_not_called()
        list_mock.assert_not_called()
        assert hits and hits[0].automation_id == "num7Button"


class TestListElementsSpySkip:
    def test_skip_spy_when_treeitem_uia_hits(self):
        assert _should_skip_spy_list("Teams", "treeitem", True) is True
        assert _should_skip_spy_list("Teams", "treeitem", False) is False

    def test_skip_spy_for_electron_when_uia_hits(self):
        with mock.patch(
            "detection.backends.uia_backend._prefer_uia_find_before_spy",
            return_value=True,
        ):
            assert _should_skip_spy_list("Teams", None, True) is True

    def test_list_elements_does_not_call_spy_when_treeitem_found(self):
        backend = UIABackend()
        wrapper = mock.Mock()
        tree_wrapper = mock.Mock()
        from detection.element_model import DetectedElement

        det = DetectedElement(
            name="Chat Awamori, Nicolas",
            role="TreeItem",
            automation_id="menur1oc",
            visible=True,
        )
        with mock.patch.object(
            backend, "is_available", return_value=True
        ), mock.patch(
            "detection.backends.uia_backend._get_desktop",
            return_value=mock.Mock(),
        ), mock.patch(
            "detection.backends.uia_backend._resolve_window",
            return_value=wrapper,
        ), mock.patch.object(
            backend,
            "_collect_descendants",
            return_value=[tree_wrapper],
        ), mock.patch(
            "detection.backends.uia_backend._pywinauto_to_element",
            return_value=det,
        ), mock.patch(
            "tools.spy_bridge.spy_available",
            return_value=True,
        ), mock.patch(
            "tools.spy_bridge.spy_list_elements",
        ) as spy_list:
            elems = backend.list_elements(
                window_title="Teams",
                max_depth=6,
                role="TreeItem",
            )
        spy_list.assert_not_called()
        assert len(elems) == 1
        assert elems[0].automation_id == "menur1oc"

    def test_collect_descendants_uses_typed_role_path(self):
        backend = UIABackend()
        window = mock.Mock()
        with mock.patch.object(
            backend,
            "_collect_typed_role_elements",
            return_value=[mock.Mock()],
        ) as typed:
            out = backend._collect_descendants(window, "control", 6, "TreeItem")
        typed.assert_called_once_with(window, 6, "treeitem")
        assert out

    def test_collect_treeitem_prefers_findall_path(self):
        backend = UIABackend()
        window = mock.Mock()
        findall_item = mock.Mock()
        with mock.patch.object(
            backend,
            "_collect_treeitem_findall",
            return_value=[findall_item],
        ) as findall, mock.patch.object(
            backend, "_window_hwnd", return_value=0
        ):
            out = backend._collect_typed_role_elements(window, 6, "treeitem")
        findall.assert_called_once_with(window, 6)
        assert out == [findall_item]

    def test_collect_treeitem_prefers_narrow_pane_path(self):
        backend = UIABackend()
        window = mock.Mock()
        narrow_item = mock.Mock()
        with mock.patch.object(
            backend,
            "_collect_treeitem_findall",
            return_value=[],
        ), mock.patch.object(
            backend,
            "_collect_treeitem_from_narrow_panes",
            return_value=[narrow_item],
        ) as narrow, mock.patch.object(
            backend, "_window_hwnd", return_value=0
        ):
            out = backend._collect_typed_role_elements(window, 6, "treeitem")
        narrow.assert_called_once_with(window, 6)
        assert out == [narrow_item]

    def test_collect_treeitem_prefers_spatial_comtypes_path(self):
        backend = UIABackend()
        window = mock.Mock()
        spatial_item = mock.Mock()
        with mock.patch.object(
            backend,
            "_collect_treeitem_findall",
            return_value=[],
        ), mock.patch.object(
            backend,
            "_collect_treeitem_from_narrow_panes",
            return_value=[],
        ), mock.patch.object(
            backend,
            "_collect_treeitem_comtypes_spatial",
            return_value=[spatial_item],
        ) as spatial, mock.patch.object(
            backend, "_collect_treeitem_via_sidebar_roots"
        ) as sidebar, mock.patch.object(
            backend, "_window_hwnd", return_value=0
        ):
            out = backend._collect_typed_role_elements(window, 6, "treeitem")
        spatial.assert_called_once_with(window, 6)
        sidebar.assert_not_called()
        assert out == [spatial_item]

    def test_collect_treeitem_prefers_sidebar_tree_roots(self):
        backend = UIABackend()
        window = mock.Mock()
        sidebar_item = mock.Mock()
        with mock.patch.object(
            backend,
            "_collect_treeitem_findall",
            return_value=[],
        ), mock.patch.object(
            backend,
            "_collect_treeitem_from_narrow_panes",
            return_value=[],
        ), mock.patch.object(
            backend,
            "_collect_treeitem_comtypes_spatial",
            return_value=[],
        ), mock.patch.object(
            backend,
            "_collect_treeitem_via_sidebar_roots",
            return_value=[sidebar_item],
        ) as sidebar, mock.patch.object(
            backend, "_window_hwnd", return_value=12345
        ):
            out = backend._collect_typed_role_elements(window, 6, "treeitem")
        sidebar.assert_called_once_with(window, 6)
        assert out == [sidebar_item]

    def test_resolve_sidebar_scroll_raw_prefers_chat_treeitem(self):
        backend = UIABackend()
        chat = mock.Mock()
        chat.element_info.element = object()
        det = mock.Mock()
        det.name = "Chat Awamori, Nicolas"
        det.y = 640
        with mock.patch(
            "detection.backends.uia_backend._pywinauto_to_element",
            return_value=det,
        ), mock.patch(
            "detection.uia_patterns.find_scrollable_ancestor",
            return_value=chat.element_info.element,
        ) as find_scroll:
            raw = backend._resolve_sidebar_scroll_raw([chat])
        find_scroll.assert_called_once_with(chat.element_info.element, max_levels=20)
        assert raw is chat.element_info.element

    def test_collect_treeitem_findall_skips_scroll_when_full(self):
        backend = UIABackend()
        window = mock.Mock()
        items = [mock.Mock() for _ in range(_SIDEBAR_TREE_FULL_ITEMS)]
        with mock.patch.object(
            backend,
            "_findall_sidebar_treeitems",
            return_value=items,
        ) as findall, mock.patch.object(
            backend,
            "_resolve_sidebar_scroll_raw",
        ) as resolve_scroll:
            out = backend._collect_treeitem_findall(window, 8)
        assert out is items
        resolve_scroll.assert_not_called()
        findall.assert_called_once()

    def test_view_scope_skipped_for_treeitem_walk_root(self):
        backend = UIABackend()
        window = mock.Mock()
        scoped = mock.Mock()
        with mock.patch.object(
            backend, "is_available", return_value=True
        ), mock.patch(
            "detection.backends.uia_backend._get_desktop",
            return_value=mock.Mock(),
        ), mock.patch(
            "detection.backends.uia_backend._resolve_window",
            return_value=window,
        ), mock.patch(
            "detection.spatial_cluster.resolve_content_walk_root",
            return_value=scoped,
        ) as resolve_root, mock.patch.object(
            backend,
            "_collect_descendants",
            return_value=[],
        ) as collect:
            backend.list_elements(
                window_title="Teams",
                max_depth=6,
                role="TreeItem",
                view_scope=True,
            )
        resolve_root.assert_not_called()
        collect.assert_called_once()
        assert collect.call_args[0][0] is window

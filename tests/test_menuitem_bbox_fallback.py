"""MenuItem bbox fallback when InvokePattern fails."""
from __future__ import annotations

from unittest import mock

from tools.ui_automation import do_click_element


class TestMenuItemBboxFallback:
    def test_click_element_menuitem_uses_bbox_when_invoke_fails(self):
        elem = {
            "name": "Copiar",
            "role": "MenuItem",
            "automation_id": "16",
            "x": 280,
            "y": 110,
            "width": 40,
            "height": 20,
            "patterns": ["Invoke"],
        }
        with mock.patch(
            "tools.ui_automation.do_find_element",
            return_value={"found": True, "elements": [elem], "backend_used": "uia"},
        ), mock.patch(
            "tools.ui_automation._try_invoke_click",
            return_value=None,
        ), mock.patch(
            "tools.ui_automation._click_coords",
            return_value=(300, 120),
        ), mock.patch(
            "tools.ui_automation.do_click",
            return_value={"success": True},
        ):
            out = do_click_element(name="Copiar", role="MenuItem", window_title="Bloc de notas")

        assert out["success"] is True
        assert out.get("method") == "MenuItem_bbox_fallback"
        assert out.get("clicked_at") == {"x": 300, "y": 120}

    def test_non_menuitem_still_skips_coords_when_identifiable(self):
        elem = {
            "name": "Guardar",
            "role": "Button",
            "automation_id": "1",
            "patterns": ["Invoke"],
        }
        with mock.patch(
            "tools.ui_automation.do_find_element",
            return_value={"found": True, "elements": [elem], "backend_used": "uia"},
        ), mock.patch(
            "tools.ui_automation._try_invoke_click",
            return_value=None,
        ):
            out = do_click_element(name="Guardar", role="Button", window_title="Guardar como")

        assert out["success"] is False
        assert "coordinate click skipped" in out.get("error", "")

    def test_click_document_uses_set_focus(self):
        elem = {
            "name": "Editor de texto",
            "role": "Document",
            "automation_id": "15",
            "patterns": ["Value"],
        }
        with mock.patch(
            "tools.ui_automation.do_find_element",
            return_value={"found": True, "elements": [elem], "backend_used": "uia"},
        ), mock.patch(
            "tools.ui_automation._try_invoke_click",
            return_value=None,
        ), mock.patch(
            "detection.backends.uia_backend.get_uia_backend",
        ) as backend_factory:
            backend = mock.MagicMock()
            backend.focus_element.return_value = {"success": True, "method": "SetFocus"}
            backend_factory.return_value = backend
            from tools.ui_automation import do_click_element

            out = do_click_element(automation_id="15", window_title="Bloc de notas")
        assert out["success"] is True
        assert out.get("method") == "SetFocus"

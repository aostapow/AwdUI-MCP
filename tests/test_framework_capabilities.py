"""Tests for framework capability matrix."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server"))


class TestFrameworkCapabilities:
    def test_winforms_screenshot_window_preferred(self):
        from detection.framework_capabilities import get_tool_capability

        cap = get_tool_capability("winforms", "screenshot_window")
        assert cap.level == "preferred"

    def test_electron_screenshot_window_blocked(self):
        from detection.framework_capabilities import get_tool_capability

        cap = get_tool_capability("electron", "screenshot_window")
        assert cap.level == "blocked"

    def test_ast_profile_is_winforms_not_electron(self):
        from detection.framework_capabilities import build_automation_profile

        profile = build_automation_profile(
            window_title="AST - Activities Manager",
            app_name="Administrador.exe",
            exe_path=r"C:\AST\Administrador.exe",
            repo_framework="winforms",
        )
        assert profile["framework"] == "winforms"
        assert profile["app_label"] == "AST Activities Manager"
        assert "not Electron" in " ".join(profile["notes"])
        assert "screenshot_window" in profile["preferred_tools"]
        assert "screenshot_window" not in profile["blocked_tools"]

    def test_ast_combo_blocks_set_element_value(self):
        from detection.framework_capabilities import check_tool_capability

        cap = check_tool_capability(
            "winforms",
            "set_element_value",
            control_role="ComboBox",
            app_storage_key="administrador.exe",
        )
        assert cap["blocked"] is True
        assert "list_control_items" in cap.get("use_instead", "")

    def test_ast_button_discourages_invoke(self):
        from detection.framework_capabilities import check_tool_capability

        cap = check_tool_capability(
            "winforms",
            "invoke_element",
            control_role="Button",
            app_storage_key="administrador.exe",
        )
        assert cap["level"] == "discouraged"
        assert cap["warning"] is True

    def test_app_framework_mismatch_warns(self):
        from detection.framework_capabilities import get_tool_capability

        cap = get_tool_capability(
            "electron",
            "find_element",
            app_storage_key="administrador.exe",
        )
        assert cap.level == "conditional"
        assert "winforms" in cap.reason

    def test_printwindow_delegates_to_matrix(self):
        from detection.framework_capabilities import printwindow_capability

        assert printwindow_capability("winforms")["compatible"] is True
        assert printwindow_capability("electron")["compatible"] is False

    def test_capability_precheck_blocks_java_swing_find_element(self):
        from detection.framework_capabilities import capability_precheck

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "tools.framework_detect.do_detect_framework",
                lambda _wt: {"framework": "java_swing"},
            )
            mp.setattr(
                "detection.app_identity.repository_app_name",
                lambda _fw, _wt: ("javaw.exe", ""),
            )
            blocked = capability_precheck("Java App", "find_element")
        assert blocked is not None
        assert blocked["success"] is False

    def test_get_automation_profile_tool(self):
        from tools.automation_profile import do_get_automation_profile

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "tools.framework_detect.do_detect_framework",
                lambda _wt: {
                    "framework": "winforms",
                    "process_name": "Administrador.exe",
                    "exe_path": r"C:\AST\Administrador.exe",
                    "hints": [],
                },
            )
            mp.setattr(
                "detection.app_identity.repository_app_name",
                lambda _fw, _wt: ("Administrador.exe", r"C:\AST\Administrador.exe"),
            )
            mp.setattr(
                "detection.object_repository.load_repo",
                lambda _n, _p: {
                    "framework": "winforms",
                    "capability_overrides": "",
                    "app_name": "Administrador.exe",
                },
            )
            profile = do_get_automation_profile("AST")
        assert profile["framework"] == "winforms"
        assert "invoke_element" in profile["tools"]

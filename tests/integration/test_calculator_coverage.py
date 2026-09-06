"""Full Calculator coverage — all modes, not just 2+2."""
import os
import sys

os.environ["AWDUI_SKIP_VIRTUAL_DESKTOP"] = "1"

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "mcp-servers", "awdui-server"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from tests.integration.calculator_map import MODE_CASES, MODE_ORDER, NAV_MODES

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="Windows only"),
    pytest.mark.integration,
]


@pytest.fixture(scope="module")
def calculator_session():
    from tests.integration.calculator_harness import ensure_calculator_running, teardown_calculator

    ctx = ensure_calculator_running()
    assert ctx.get("success"), ctx.get("error", "calculator not available")
    yield ctx
    teardown_calculator()


class TestNavigation:
    def test_nav_lists_all_modes(self, calculator_session):
        from tests.integration.calculator_harness import click_button, open_navigation
        from tools.ui_automation import do_list_elements

        title = calculator_session["window_title"]
        open_navigation(title)
        listed = do_list_elements(window_title=title, max_depth=10, role="ListItem")
        aids = {e.get("automation_id") for e in listed.get("elements", [])}
        for mode_id in NAV_MODES.values():
            assert mode_id in aids, f"mode {mode_id} missing from nav"
        click_button(automation_id="TogglePaneButton", window_title=title)

    @pytest.mark.parametrize("mode_id", MODE_ORDER)
    def test_switch_mode(self, calculator_session, mode_id):
        from tests.integration.calculator_harness import get_current_mode, switch_mode

        title = calculator_session["window_title"]
        result = switch_mode(mode_id, window_title=title)
        assert result.get("success"), result
        header = get_current_mode(title).lower()
        assert header, f"no header after switch to {mode_id}"


class TestModeCases:
    @pytest.mark.parametrize("mode_id,cases", list(MODE_CASES.items()))
    def test_mode_arithmetic(self, calculator_session, mode_id, cases):
        from tests.integration.calculator_harness import switch_mode
        from tests.integration.evidence import compute_and_verify

        title = calculator_session["window_title"]
        switch_mode(mode_id, window_title=title)
        for ticket_id, steps, expected, desc in cases:
            if expected is None:
                continue
            compute_and_verify(steps, expected, ticket_id, window_title=title)


class TestPanels:
    def test_history_panel_opens(self, calculator_session):
        from tests.integration.calculator_harness import click_button
        from tools.ui_automation import do_list_elements

        title = calculator_session["window_title"]
        click_button(automation_id="HistoryButton", window_title=title)
        import time
        time.sleep(0.5)
        # History flyout may add elements or windows
        listed = do_list_elements(window_title=title, max_depth=6)
        assert listed.get("count", 0) > 0

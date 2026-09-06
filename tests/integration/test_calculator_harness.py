"""Calculator harness smoke — launch and find keypad."""
import os
import sys

os.environ["AWDUI_SKIP_VIRTUAL_DESKTOP"] = "1"

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "mcp-servers", "awdui-server"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="Windows only"),
    pytest.mark.integration,
]


@pytest.fixture
def calculator_session():
    from tests.integration.calculator_harness import ensure_calculator_running, teardown_calculator

    ctx = ensure_calculator_running()
    assert ctx.get("success"), ctx.get("error", "calculator not available")
    yield ctx
    teardown_calculator()


class TestCalculatorHarness:
    def test_launch_and_find_num1(self, calculator_session):
        from tools.ui_automation import do_find_element

        title = calculator_session["window_title"]
        found = do_find_element(automation_id="num1Button", window_title=title)
        assert found.get("found") is True

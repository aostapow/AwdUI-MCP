"""Compare repo_action (direct path) vs click_element timing."""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp-servers" / "awdui-server"))

WINDOW = "Calculadora"
STEPS = [
    ("Calculadora/clearButton", "clear"),
    ("Calculadora/num1Button", "1"),
    ("Calculadora/num5Button", "5"),
    ("Calculadora/multiplyButton", "*"),
    ("Calculadora/num7Button", "7"),
    ("Calculadora/equalButton", "="),
]


def main() -> None:
    from tools.target_window import set_target
    from tools.windows import do_focus_window
    from tools.repo_action import do_repo_action

    set_target(WINDOW)
    do_focus_window(WINDOW, "focus")
    time.sleep(0.3)

    print("repo_action direct paths — 15 * 7")
    total = 0.0
    for path, label in STEPS:
        t0 = time.perf_counter()
        r = do_repo_action(path, "Click", window_title=WINDOW, highlight=False)
        elapsed = time.perf_counter() - t0
        total += elapsed
        ok = "OK" if r.get("success") else "FAIL"
        method = r.get("method", r.get("error", ""))
        print(f"  {elapsed*1000:6.0f}ms  {ok}  {label:6}  {method}")
    print(f"  subtotal: {total*1000:.0f}ms")


if __name__ == "__main__":
    main()

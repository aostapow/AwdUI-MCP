"""Benchmark calculator automation via object repository (no screenshots)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "mcp-servers" / "awdui-server"
sys.path.insert(0, str(SERVER))

WINDOW = "Calculadora"


def _step(label: str, fn) -> float:
    t0 = time.perf_counter()
    result = fn()
    elapsed = time.perf_counter() - t0
    ok = True
    if isinstance(result, dict):
        ok = result.get("success", result.get("found", True))
    status = "OK" if ok else "FAIL"
    layer = ""
    if isinstance(result, dict):
        layer = result.get("layer") or result.get("method") or result.get("backend_used") or ""
        if result.get("repo_path"):
            layer = f"{layer} ({result['repo_path']})"
    print(f"  {elapsed*1000:6.0f}ms  {status:4}  {label:20}  {layer}")
    if not ok:
        err = result.get("error", result) if isinstance(result, dict) else result
        print(f"           -> {err}")
    return elapsed


def _click_digit(d: str):
    from tools.ui_automation import do_click_element
    return do_click_element(name=d, window_title=WINDOW, remember=False)


def _click_auto(aid: str, label: str):
    from tools.ui_automation import do_click_element
    return do_click_element(automation_id=aid, window_title=WINDOW, remember=False)


def run_expression(expr: str, steps: list[tuple[str, callable]]) -> float:
    print(f"\n=== {expr} ===")
    total = 0.0
    for label, fn in steps:
        total += _step(label, fn)
    print(f"  {'':6}  ----  subtotal: {total*1000:.0f}ms")
    return total


def main() -> int:
    from tools.target_window import set_target
    from tools.windows import do_focus_window

    print("Calculator repo benchmark (capture=false, remember=false)")
    set_target(WINDOW)
    do_focus_window(WINDOW, "focus")
    time.sleep(0.3)

    grand = 0.0

    # Expression 1: 15 * 7
    grand += run_expression(
        "15 * 7",
        [
            ("clear", lambda: _click_auto("clearButton", "clear")),
            ("1", lambda: _click_digit("1")),
            ("5", lambda: _click_digit("5")),
            ("*", lambda: _click_auto("multiplyButton", "*")),
            ("7", lambda: _click_digit("7")),
            ("=", lambda: _click_auto("equalButton", "=")),
        ],
    )
    time.sleep(0.4)

    # Expression 2: 12 + 8
    grand += run_expression(
        "12 + 8",
        [
            ("clear", lambda: _click_auto("clearButton", "clear")),
            ("1", lambda: _click_digit("1")),
            ("2", lambda: _click_digit("2")),
            ("+", lambda: _click_auto("plusButton", "+")),
            ("8", lambda: _click_digit("8")),
            ("=", lambda: _click_auto("equalButton", "=")),
        ],
    )
    time.sleep(0.4)

    # Expression 3: 100 / 4
    grand += run_expression(
        "100 / 4",
        [
            ("clear", lambda: _click_auto("clearButton", "clear")),
            ("1", lambda: _click_digit("1")),
            ("0", lambda: _click_digit("0")),
            ("0", lambda: _click_digit("0")),
            ("/", lambda: _click_auto("divideButton", "/")),
            ("4", lambda: _click_digit("4")),
            ("=", lambda: _click_auto("equalButton", "=")),
        ],
    )

    print(f"\n=== TOTAL {grand*1000:.0f}ms for 19 clicks across 3 expressions ===")
    print("Expected display after last: 25")

    try:
        from tools.screenshot import capture_screenshot
        import base64
        from io import BytesIO
        from PIL import Image

        shot = capture_screenshot(window_title=WINDOW)
        out = Path.home() / ".awdui-mcp" / "benchmark_calc_result.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        if shot.get("path"):
            import shutil
            shutil.copy(shot["path"], out)
        elif shot.get("image"):
            Image.open(BytesIO(base64.b64decode(shot["image"]))).save(out)
        print(f"Screenshot: {out}")
    except Exception as exc:
        print(f"Screenshot skipped: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

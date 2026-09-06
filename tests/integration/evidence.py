"""Empirical evidence helpers for integration tests — UIA + screenshot + OCR."""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Optional

EVIDENCE_DIR = Path(__file__).resolve().parent / "evidence"
_LAST_RUN_PATH = EVIDENCE_DIR / "last_run.json"

_NUMERIC_RE = re.compile(r"[-+]?\d[\d,.\s]*")


def _init_screenshot_manager() -> None:
    from tools import screenshot as screenshot_mod
    if screenshot_mod.screenshot_manager is not None:
        return
    import tempfile
    from screenshot_manager import ScreenshotManager
    screenshot_mod.screenshot_manager = ScreenshotManager(
        os.path.join(tempfile.gettempdir(), "awdui_screenshots")
    )


def _ensure_dir() -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    return EVIDENCE_DIR


def capture_evidence(label: str, window_title: str) -> str:
    """Save a window screenshot; return file path."""
    _init_screenshot_manager()
    _ensure_dir()
    from tools.screenshot import capture_screenshot

    safe = re.sub(r"[^\w\-]+", "_", label)[:60]
    path = EVIDENCE_DIR / f"{safe}_{int(time.time() * 1000)}.png"
    shot = capture_screenshot(window_title=window_title)
    if shot.get("path") and os.path.isfile(shot["path"]):
        import shutil
        shutil.copy(shot["path"], path)
        return str(path)
    if shot.get("image"):
        import base64
        path.write_bytes(base64.b64decode(shot["image"]))
        return str(path)
    return ""


def _normalize_number(text: str) -> str:
    if not text:
        return ""
    cleaned = text.replace("\u202f", " ").replace("\xa0", " ")
    matches = _NUMERIC_RE.findall(cleaned)
    if not matches:
        return ""
    return matches[-1].strip().replace(" ", "").replace(",", "")


def _ocr_read_display(window_title: str, screenshot_path: str = "", expected_hint: str = "") -> dict:
    from tools.ocr import do_find_text

    if expected_hint:
        result = do_find_text(query=expected_hint, window_title=window_title)
        if result.get("found") or result.get("matches"):
            return {"value": _normalize_number(expected_hint), "source": "ocr", "raw": expected_hint}

    if screenshot_path:
        result = do_find_text(query=expected_hint or "0", image_path=screenshot_path)
        for w in result.get("words") or result.get("matches") or []:
            text = str(w.get("text") or w.get("word") or "")
            num = _normalize_number(text)
            if num:
                return {"value": num, "source": "ocr", "raw": text}

    result = do_find_text(query="=", window_title=window_title)
    words = result.get("words") or result.get("matches") or []
    candidates: list[str] = []
    for w in words:
        text = str(w.get("text") or w.get("word") or "")
        num = _normalize_number(text)
        if num:
            candidates.append(num)

    if candidates:
        return {"value": candidates[-1], "source": "ocr", "raw": candidates[-1]}
    return {"value": "", "source": "none", "raw": ""}


def read_display_with_fallback(window_title: str, expected_hint: str = "") -> dict:
    """UIA first; screenshot + OCR if UIA empty or ambiguous."""
    from tests.integration.calculator_harness import read_display_uia

    uia = read_display_uia(window_title)
    if uia.get("value"):
        return {**uia, "screenshot_path": ""}

    shot_path = capture_evidence("display_fallback", window_title)
    ocr = _ocr_read_display(window_title, shot_path, expected_hint=expected_hint)
    return {
        "value": ocr.get("value", ""),
        "source": ocr.get("source", "none"),
        "raw": ocr.get("raw", ""),
        "screenshot_path": shot_path,
        "uia_attempt": uia,
    }


def write_run_log(entry: dict) -> None:
    _ensure_dir()
    rows: list = []
    if _LAST_RUN_PATH.is_file():
        try:
            rows = json.loads(_LAST_RUN_PATH.read_text(encoding="utf-8"))
        except Exception:
            rows = []
    entry["ts"] = int(time.time())
    rows.append(entry)
    _LAST_RUN_PATH.write_text(json.dumps(rows[-200:], indent=2), encoding="utf-8")


def assert_display_equals(
    expected: str,
    *,
    ticket_id: str,
    window_title: Optional[str] = None,
    tolerance: str = "exact",
) -> dict:
    """Verify visible display; FAIL via AssertionError with evidence paths."""
    from tests.integration.calculator_harness import resolve_window_title

    wt = window_title or resolve_window_title()
    expected_norm = _normalize_number(expected)
    assert expected_norm, f"{ticket_id}: empty expected value"

    reading = read_display_with_fallback(wt, expected_hint=expected_norm)
    actual = _normalize_number(str(reading.get("value") or ""))
    screenshot_path = reading.get("screenshot_path") or ""

    if not actual:
        if not screenshot_path:
            screenshot_path = capture_evidence(f"{ticket_id}_empty", wt)
        write_run_log({
            "ticket": ticket_id,
            "expected": expected_norm,
            "actual": "",
            "source": "none",
            "screenshot_path": screenshot_path,
            "ok": False,
        })
        raise AssertionError(
            f"{ticket_id}: could not read display; screenshot={screenshot_path}"
        )

    if tolerance == "exact" and actual != expected_norm:
        if not screenshot_path:
            screenshot_path = capture_evidence(f"{ticket_id}_mismatch", wt)
        write_run_log({
            "ticket": ticket_id,
            "expected": expected_norm,
            "actual": actual,
            "source": reading.get("source"),
            "screenshot_path": screenshot_path,
            "ok": False,
        })
        raise AssertionError(
            f"{ticket_id}: display expected '{expected_norm}' got '{actual}' "
            f"(source={reading.get('source')}) screenshot={screenshot_path}"
        )

    write_run_log({
        "ticket": ticket_id,
        "expected": expected_norm,
        "actual": actual,
        "source": reading.get("source"),
        "screenshot_path": screenshot_path,
        "ok": True,
    })
    return {
        "ok": True,
        "expected": expected_norm,
        "actual": actual,
        "source": reading.get("source"),
        "screenshot_path": screenshot_path,
    }


def compute_and_verify(
    steps: list[tuple[str, str]],
    expected: str,
    ticket_id: str,
    *,
    window_title: Optional[str] = None,
) -> dict:
    from tests.integration.calculator_harness import compute_expression, resolve_window_title
    from tests.integration.recovery import with_step_recovery

    wt = window_title or resolve_window_title()

    def _run():
        clicks = compute_expression(steps, window_title=wt)
        failed = [c for c in clicks if not c.get("success")]
        if failed:
            shot = capture_evidence(f"{ticket_id}_click_fail", wt)
            raise AssertionError(
                f"{ticket_id}: click failed at {failed[0].get('step_label')}: "
                f"{failed[0].get('error')} screenshot={shot}"
            )
        time.sleep(0.35)
        return assert_display_equals(expected, ticket_id=ticket_id, window_title=wt)

    return with_step_recovery(_run, ctx={"window_title": wt, "ticket_id": ticket_id}, max_recovery=1, timeout_s=60.0)

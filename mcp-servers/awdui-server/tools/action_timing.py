"""Action timing — measure find / act / verify phases for MCP efficiency."""
from __future__ import annotations

import time
from typing import Any, Optional

# Targets from awdui-mcp-objective skill.
FAST_TARGET_MS = 500
SLOW_WARN_MS = 3000


class ActionTimer:
    """Track phased timings for a single MCP action."""

    def __init__(self) -> None:
        self._t0 = time.perf_counter()
        self._open: Optional[str] = None
        self._open_t = 0.0
        self.phases: dict[str, int] = {}

    def start(self, phase: str) -> None:
        if self._open:
            self.end()
        self._open = phase
        self._open_t = time.perf_counter()

    def end(self) -> None:
        if not self._open:
            return
        ms = int((time.perf_counter() - self._open_t) * 1000)
        self.phases[f"{self._open}_ms"] = ms
        self._open = None

    def mark(self, key: str, ms: int) -> None:
        if not key.endswith("_ms"):
            key = f"{key}_ms"
        self.phases[key] = int(ms)

    def attach(self, result: dict[str, Any]) -> dict[str, Any]:
        if self._open:
            self.end()
        total = int((time.perf_counter() - self._t0) * 1000)
        timing = {**self.phases, "total_ms": total}
        result["elapsed_ms"] = total
        result["timing"] = timing
        result["performance"] = classify_performance(total)
        return result


def classify_performance(total_ms: int) -> str:
    if total_ms >= SLOW_WARN_MS:
        return "slow"
    if total_ms >= FAST_TARGET_MS:
        return "ok"
    return "fast"


def format_timing_suffix(result: dict[str, Any]) -> str:
    """Human-readable timing for MCP tool text responses."""
    timing = result.get("timing") or {}
    total = result.get("elapsed_ms") or timing.get("total_ms")
    if total is None:
        return ""

    parts: list[str] = []
    for key in ("probe_ms", "find_ms", "act_ms", "verify_ms", "list_ms"):
        if key in timing:
            label = key.replace("_ms", "")
            parts.append(f"{label} {timing[key]}ms")

    perf = result.get("performance") or classify_performance(int(total))
    slow_flag = " ⚠ SLOW" if perf == "slow" else ""
    if parts:
        return f" (total {total}ms: {', '.join(parts)}){slow_flag}"
    return f" ({total}ms){slow_flag}"


def format_verify_suffix(result: dict[str, Any]) -> str:
    verified = result.get("verified")
    if verified is True:
        return " ✓ verified"
    if verified is False:
        detail = result.get("verify_error") or result.get("verify_detail") or "check failed"
        return f" ✗ verify failed: {detail}"
    return ""


def run_post_act_verify(
    *,
    window_title: Optional[str] = None,
    verify_automation_id: Optional[str] = None,
    verify_name_contains: Optional[str] = None,
    timeout_ms: int = 5000,
    poll_ms: int = 100,
) -> dict[str, Any]:
    """Poll UIA until post-act verify passes (delegates to wait_tools)."""
    t0 = time.perf_counter()
    aid = (verify_automation_id or "").strip()
    needle = (verify_name_contains or "").strip()
    if not aid and not needle:
        return {"verified": None, "verify_ms": 0}

    from tools.wait_tools import do_wait_for_condition, do_wait_for_element

    if needle:
        result = do_wait_for_condition(
            property="name",
            expected_value=needle,
            automation_id=aid or None,
            window_title=window_title,
            timeout_ms=timeout_ms,
            poll_ms=poll_ms,
        )
        verify_ms = int((time.perf_counter() - t0) * 1000)
        if result.get("success"):
            return {
                "verified": True,
                "verify_ms": verify_ms,
                "verify_name": result.get("actual", ""),
                "verify_attempts": result.get("attempts"),
            }
        actual = str(result.get("actual") or "")
        err = result.get("error") or "timeout"
        if actual and err == "timeout":
            err = f"name does not contain '{needle}'"
        return {
            "verified": False,
            "verify_ms": verify_ms,
            "verify_error": err,
            "actual_name": actual,
            "verify_attempts": result.get("attempts"),
        }

    if aid:
        result = do_wait_for_element(
            automation_id=aid,
            window_title=window_title,
            timeout_ms=timeout_ms,
            poll_ms=poll_ms,
        )
        verify_ms = int((time.perf_counter() - t0) * 1000)
        if result.get("success"):
            elem = result.get("element") or {}
            return {
                "verified": True,
                "verify_ms": verify_ms,
                "verify_name": elem.get("name", ""),
                "verify_attempts": result.get("attempts"),
            }
        return {
            "verified": False,
            "verify_ms": verify_ms,
            "verify_error": result.get("error", "timeout"),
            "verify_attempts": result.get("attempts"),
        }

    return {"verified": None, "verify_ms": 0}


def attach_simple_elapsed(result: dict[str, Any], t0: float) -> dict[str, Any]:
    """Single-phase timing (find-only or list-only tools)."""
    ms = int((time.perf_counter() - t0) * 1000)
    phase_key = "list_ms" if "elements" in result and "found" not in result else "find_ms"
    result["elapsed_ms"] = ms
    result["timing"] = {phase_key: ms, "total_ms": ms}
    result["performance"] = classify_performance(ms)
    return result

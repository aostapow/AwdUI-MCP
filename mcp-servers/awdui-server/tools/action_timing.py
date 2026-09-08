"""Action timing — measure find / act / verify phases for MCP efficiency."""
from __future__ import annotations

import time
from typing import Any, Optional

# Targets from awdui-mcp-automejora skill.
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
        phase_sum = sum(
            int(v) for k, v in self.phases.items() if str(k).endswith("_ms")
        )
        operational = phase_sum if phase_sum > 0 else total
        timing = {**self.phases, "total_ms": total, "operational_ms": operational}
        result["elapsed_ms"] = operational
        result["timing"] = timing
        result["performance"] = classify_performance(operational)
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
    total = result.get("elapsed_ms") or timing.get("operational_ms") or timing.get("total_ms")
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
    if result.get("modal_dismissed") is True:
        return " ✓ modal dismissed"
    if verified is True:
        return " ✓ verified"
    if verified is False:
        detail = result.get("verify_error") or result.get("verify_detail") or "check failed"
        if result.get("modal_still_open"):
            detail = f"modal still open: {result['modal_still_open']}"
        return f" ✗ verify failed: {detail}"
    return ""


def run_post_act_verify(
    *,
    window_title: Optional[str] = None,
    verify_automation_id: Optional[str] = None,
    verify_name_contains: Optional[str] = None,
    verify_modal_dismissed: bool = False,
    modal_title: Optional[str] = None,
    parent_pid: Optional[int] = None,
    timeout_ms: int = 5000,
    poll_ms: int = 100,
) -> dict[str, Any]:
    """Poll UIA or window list until post-act verify passes."""
    t0 = time.perf_counter()

    if verify_modal_dismissed:
        title = (modal_title or window_title or "").strip()
        if not title:
            return {
                "verified": False,
                "verify_ms": 0,
                "verify_error": "modal_title required for verify_modal_dismissed",
            }
        deadline = t0 + max(timeout_ms, poll_ms) / 1000.0
        interval = max(poll_ms, 50) / 1000.0
        while time.perf_counter() < deadline:
            from tools.window_scope import modal_title_visible

            if not modal_title_visible(title, parent_pid=parent_pid):
                verify_ms = int((time.perf_counter() - t0) * 1000)
                return {
                    "verified": True,
                    "modal_dismissed": True,
                    "verify_ms": verify_ms,
                }
            time.sleep(interval)
        verify_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "verified": False,
            "modal_dismissed": False,
            "modal_still_open": title,
            "verify_ms": verify_ms,
            "verify_error": "modal still in list_windows",
            "hint": (
                "recovery L1: focus_window + Cancelar; do not trust act-only success"
            ),
        }

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


def snapshot_header_name(window_title: Optional[str] = None) -> str:
    """Read Header automation_id text before Nav/list selection acts."""
    from tools.wait_tools import _read_properties

    props = _read_properties(automation_id="Header", window_title=window_title)
    return str((props or {}).get("name") or "")


def snapshot_selection_prestate(window_title: Optional[str] = None) -> dict[str, str]:
    """Capture header + window title before SelectionItem acts (NavView / chat list)."""
    from tools.target_window import get_target

    wt = (get_target() or window_title or "").strip()
    return {
        "header_name": snapshot_header_name(window_title),
        "window_title": wt,
    }


def _contact_needles_from_acted_name(name: Optional[str]) -> list[str]:
    """Extract stable contact tokens from chat TreeItem/ListItem names (app-agnostic)."""
    raw = (name or "").strip()
    if not raw:
        return []
    lowered = raw.lower()
    if lowered.startswith("chat "):
        raw = raw[5:].strip()
    for sep in (" sin ", " ausente", " tiene ", " silenciado", " no leído"):
        idx = raw.lower().find(sep)
        if idx > 0:
            raw = raw[:idx].strip()
    needles: list[str] = []
    if raw:
        needles.append(raw)
        if "," in raw:
            needles.append(raw.split(",", 1)[0].strip())
        first = raw.split()[0] if raw.split() else ""
        if first and first not in needles:
            needles.append(first)
    return [n for n in needles if len(n) >= 3]


def _current_window_title(window_title: Optional[str] = None) -> str:
    from tools.target_window import get_target, get_target_hwnd

    hwnd = get_target_hwnd()
    if hwnd:
        try:
            import ctypes

            user32 = ctypes.windll.user32
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                live = (buf.value or "").strip()
                if live:
                    return live
        except Exception:
            pass
    return (get_target() or window_title or "").strip()


def _title_contact_hit(
    *,
    pre_wt: str,
    needles: list[str],
    window_title: Optional[str],
    allow_stable: bool = False,
) -> Optional[dict[str, Any]]:
    """Fast verify via live window title only (no UIA)."""
    current = _current_window_title(window_title)
    if not current:
        return None
    current_lower = current.lower()
    for needle in needles:
        if needle.lower() not in current_lower:
            continue
        if not pre_wt or needle.lower() not in pre_wt.lower() or current != pre_wt:
            return {
                "verified": True,
                "verify_method": "WindowTitle.contact",
                "verify_name": current,
                "contact_needle": needle,
            }
        if allow_stable:
            return {
                "verified": True,
                "verify_method": "WindowTitle.stable",
                "verify_name": current,
                "contact_needle": needle,
            }
    return None


def _verify_chat_context_ready(
    *,
    window_title: Optional[str],
    needles: list[str],
) -> Optional[dict[str, Any]]:
    """Electron/chat apps: title contains contact + compose Edit visible."""
    if not needles:
        return None
    current = _current_window_title(window_title)
    if not any(n.lower() in current.lower() for n in needles):
        return None
    from tools.wait_tools import _read_properties

    compose = _read_properties(
        name="Escribe un mensaje",
        window_title=current or window_title,
    )
    if not compose:
        return None
    return {
        "verified": True,
        "verify_method": "ChatContext.compose_ready",
        "verify_name": current,
    }


def _run_treeitem_title_verify(
    *,
    window_title: Optional[str],
    acted_automation_id: str,
    acted_name: Optional[str],
    acted_role: Optional[str],
    pre_wt: str,
    needles: list[str],
    t0: float,
    deadline: float,
    poll_ms: int,
) -> dict[str, Any]:
    """Teams/Electron chat list: poll title only, then at most one UIA read."""
    from tools.wait_tools import _read_properties

    stable = _title_contact_hit(
        pre_wt=pre_wt,
        needles=needles,
        window_title=window_title,
        allow_stable=True,
    )
    if stable:
        stable["verify_ms"] = int((time.perf_counter() - t0) * 1000)
        return stable

    interval = max(min(poll_ms, 50), 25) / 1000.0
    while time.perf_counter() < deadline:
        hit = _title_contact_hit(
            pre_wt=pre_wt,
            needles=needles,
            window_title=window_title,
        )
        if hit:
            hit["verify_ms"] = int((time.perf_counter() - t0) * 1000)
            return hit
        current = _current_window_title(window_title)
        if pre_wt and current and current != pre_wt:
            return {
                "verified": True,
                "verify_ms": int((time.perf_counter() - t0) * 1000),
                "verify_method": "WindowTitle.changed",
                "verify_name": current,
            }
        time.sleep(interval)

    hit = _title_contact_hit(
        pre_wt=pre_wt,
        needles=needles,
        window_title=window_title,
        allow_stable=True,
    )
    if hit:
        hit["verify_ms"] = int((time.perf_counter() - t0) * 1000)
        return hit

    remaining = deadline - time.perf_counter()
    if remaining > 0.15:
        ctx = _verify_chat_context_ready(window_title=window_title, needles=needles)
        if ctx:
            ctx["verify_ms"] = int((time.perf_counter() - t0) * 1000)
            return ctx

    aid = acted_automation_id.strip()
    if aid and time.perf_counter() < deadline + 0.05:
        props = _read_properties(
            automation_id=aid,
            name=acted_name or None,
            role=acted_role or None,
            window_title=window_title,
        )
        if props:
            sel = (props.get("patterns") or {}).get("SelectionItem") or {}
            flag = sel.get("is_selected") or sel.get("value")
            if flag is True or str(flag).lower() == "true":
                return {
                    "verified": True,
                    "verify_ms": int((time.perf_counter() - t0) * 1000),
                    "verify_method": "SelectionItem.is_selected",
                    "verify_name": props.get("name", ""),
                }

    verify_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "verified": False,
        "verify_ms": verify_ms,
        "verify_error": "SelectionItem verify: chat title/context unchanged",
        "pre_window_title": pre_wt,
    }


def run_selection_item_verify(
    *,
    window_title: Optional[str] = None,
    acted_automation_id: Optional[str] = None,
    acted_name: Optional[str] = None,
    acted_role: Optional[str] = None,
    pre_header_name: Optional[str] = None,
    pre_window_title: Optional[str] = None,
    timeout_ms: int = 2500,
    poll_ms: int = 100,
) -> dict[str, Any]:
    """Verify SelectionItem without waiting for offscreen Nav ListItem nodes."""
    from tools.wait_tools import _norm_text, _read_properties

    t0 = time.perf_counter()
    aid = (acted_automation_id or "").strip()
    role = (acted_role or "").strip().lower()
    pre_header = _norm_text(pre_header_name)
    pre_wt = (pre_window_title or "").strip()
    needles = _contact_needles_from_acted_name(acted_name)
    deadline = t0 + max(timeout_ms, poll_ms) / 1000.0
    interval = max(poll_ms, 50) / 1000.0

    if role == "treeitem" and needles:
        return _run_treeitem_title_verify(
            window_title=window_title,
            acted_automation_id=aid,
            acted_name=acted_name,
            acted_role=acted_role,
            pre_wt=pre_wt,
            needles=needles,
            t0=t0,
            deadline=deadline,
            poll_ms=poll_ms,
        )

    def _unwrap_flag(raw: Any) -> Any:
        if isinstance(raw, dict):
            if "Value" in raw:
                return raw.get("Value")
            if "value" in raw:
                return raw.get("value")
        return raw

    def _is_selected(props: dict) -> bool:
        sel = (props.get("patterns") or {}).get("SelectionItem") or {}
        flag = _unwrap_flag(sel.get("is_selected"))
        if flag is None:
            flag = _unwrap_flag(sel.get("value"))
        if flag is True or str(flag).lower() == "true":
            return True
        leg = (props.get("patterns") or {}).get("LegacyIAccessible") or {}
        state = leg.get("state")
        if state is None:
            state = leg.get("State")
        if state is not None:
            try:
                return bool(int(state) & 0x2)
            except (TypeError, ValueError):
                pass
        return False

    check_header = role in ("listitem", "treeitem", "tabitem", "dataitem") or (
        not role and aid.lower().endswith("item")
    )

    while time.perf_counter() < deadline:
        if check_header and needles:
            hit = _title_contact_hit(
                pre_wt=pre_wt,
                needles=needles,
                window_title=window_title,
            )
            if hit:
                hit["verify_ms"] = int((time.perf_counter() - t0) * 1000)
                return hit

        if time.perf_counter() >= deadline:
            break

        if check_header and pre_header:
            header_props = _read_properties(automation_id="Header", window_title=window_title)
            if header_props:
                header_name = _norm_text(header_props.get("name"))
                if header_name and header_name != pre_header:
                    verify_ms = int((time.perf_counter() - t0) * 1000)
                    return {
                        "verified": True,
                        "verify_ms": verify_ms,
                        "verify_method": "Header.changed",
                        "verify_name": header_props.get("name", ""),
                        "pre_header": pre_header_name or "",
                    }

        if time.perf_counter() >= deadline:
            break

        if aid:
            props = _read_properties(
                automation_id=aid,
                name=acted_name or None,
                role=acted_role or None,
                window_title=window_title,
            )
            if props and _is_selected(props):
                verify_ms = int((time.perf_counter() - t0) * 1000)
                return {
                    "verified": True,
                    "verify_ms": verify_ms,
                    "verify_method": "SelectionItem.is_selected",
                    "verify_name": props.get("name", ""),
                }

        if time.perf_counter() >= deadline:
            break

        if check_header:
            header_props = _read_properties(automation_id="Header", window_title=window_title)
            if header_props:
                header_name = _norm_text(header_props.get("name"))
                if header_name and header_name != pre_header:
                    verify_ms = int((time.perf_counter() - t0) * 1000)
                    return {
                        "verified": True,
                        "verify_ms": verify_ms,
                        "verify_method": "Header.changed",
                        "verify_name": header_props.get("name", ""),
                        "pre_header": pre_header_name or "",
                    }

        time.sleep(interval)

    verify_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "verified": False,
        "verify_ms": verify_ms,
        "verify_error": "SelectionItem verify: header/selection unchanged",
        "pre_header": pre_header_name or "",
    }


def attach_simple_elapsed(result: dict[str, Any], t0: float) -> dict[str, Any]:
    """Single-phase timing (find-only or list-only tools)."""
    ms = int((time.perf_counter() - t0) * 1000)
    phase_key = "list_ms" if "elements" in result and "found" not in result else "find_ms"
    result["elapsed_ms"] = ms
    result["timing"] = {phase_key: ms, "total_ms": ms}
    result["performance"] = classify_performance(ms)
    return result

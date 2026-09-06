"""Render UI element trees as a compact ASCII map (agent 'eye' view)."""
from __future__ import annotations

import re
from typing import Any, Optional

from detection.ascii_ui_tree import prepare_elements_for_render

_SKIP_ROLES = frozenset(
    {
        "Pane",
        "Group",
        "TitleBar",
        "ToolBar",
        "StatusBar",
        "Separator",
        "Thumb",
        "ScrollBar",
        "AppBar",
    }
)

_INTERACTIVE_ROLES = frozenset(
    {
        "Button",
        "Edit",
        "Text",
        "ComboBox",
        "ListItem",
        "List",
        "MenuItem",
        "CheckBox",
        "RadioButton",
        "TabItem",
        "Hyperlink",
        "Slider",
        "Spinner",
        "DataItem",
        "TreeItem",
        "Table",
        "DataGrid",
        "Calendar",
        "Image",
        "Custom",
    }
)

_UNICODE_BOX: dict[str, str] = {
    "tl": "┌",
    "tr": "┐",
    "bl": "└",
    "br": "┘",
    "h": "─",
    "v": "│",
}

_ASCII_BOX: dict[str, str] = {
    "tl": "+",
    "tr": "+",
    "bl": "+",
    "br": "+",
    "h": "-",
    "v": "|",
}

_BORDER_CHARS = frozenset("┌┐└┘─│+-|")

_CIRCLED = [
    "①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩",
    "⑪", "⑫", "⑬", "⑭", "⑮", "⑯", "⑰", "⑱", "⑲", "⑳",
]

_FOCUSABLE_ROLES = frozenset(
    {
        "button", "checkbox", "radiobutton", "combobox", "menuitem",
        "tabitem", "edit", "text", "hyperlink", "slider", "spinner",
        "listitem", "dataitem",
    }
)

_BASIC_ROLES = frozenset(
    {
        "Button", "Edit", "Text", "ComboBox", "ListItem", "CheckBox",
        "RadioButton", "Hyperlink", "DataItem",
    }
)


def _norm_role(role: str) -> str:
    s = (role or "").strip().lower().lstrip("ax")
    return s.replace("_", "").replace("-", "").replace(" ", "")


def _is_focusable(elem: dict[str, Any]) -> bool:
    if elem.get("is_keyboard_focusable"):
        return True
    if elem.get("has_focus"):
        return True
    return _norm_role(elem.get("role") or "") in _FOCUSABLE_ROLES


def _legend_key(index: int) -> str:
    return f"e{index + 1}"


def _tab_glyph(tab_index: int) -> str:
    if 1 <= tab_index <= len(_CIRCLED):
        return _CIRCLED[tab_index - 1]
    return f"#{tab_index}"


def _elem_key(elem: dict[str, Any]) -> tuple:
    return (
        (elem.get("automation_id") or "").strip(),
        int(elem.get("x") or 0),
        int(elem.get("y") or 0),
        (elem.get("role") or "").strip(),
    )


_AID_SUFFIXES = ("Button", "Btn", "Control", "Item", "Hyperlink", "TextBox", "Edit")

# Generic glyphs from common English automation_id tokens (locale-independent UI chrome).
_AID_GLYPHS: dict[str, str] = {
    "plus": "+",
    "minus": "−",
    "multiply": "×",
    "divide": "÷",
    "equal": "=",
    "percent": "%",
    "negate": "±",
    "decimalseparator": ",",
    "backspace": "⌫",
    "clear": "C",
    "clearentry": "CE",
    "invert": "1/x",
    "xpower2": "x²",
    "squareroot": "√",
    "clearmemory": "MC",
    "memrecall": "MR",
    "memplus": "M+",
    "memminus": "M−",
    "membutton": "M˅",
    "memorybutton": "M˅",
    "mem": "M˅",
    "historybutton": "⏱",
}


def _aid_token(aid: str) -> str:
    token = (aid or "").strip()
    for suf in _AID_SUFFIXES:
        if token.endswith(suf):
            token = token[: -len(suf)]
            break
    return token


def _glyph_from_aid(aid: str) -> str:
    raw = (aid or "").strip()
    if not raw:
        return ""
    low = raw.lower()
    if low in _AID_GLYPHS:
        return _AID_GLYPHS[low]
    token = _aid_token(raw)
    if not token:
        return ""
    low_tok = token.lower()
    if low_tok in _AID_GLYPHS:
        return _AID_GLYPHS[low_tok]
    if low_tok.startswith("num") and low_tok[3:].isdigit():
        return low_tok[3:]
    if len(token) <= 4:
        return token
    return ""


def _label_for(elem: dict[str, Any]) -> str:
    return _compact_label(elem)


def _compact_label(elem: dict[str, Any]) -> str:
    """Short on-screen label for ASCII cells (prefers glyphs over long locale names)."""
    name = re.sub(r"\s+", " ", (elem.get("name") or "").strip())
    aid = (elem.get("automation_id") or "").strip()
    value = re.sub(r"\s+", " ", (elem.get("value") or "").strip())
    role = _norm_role(elem.get("role") or "")

    glyph = _glyph_from_aid(aid)
    if glyph:
        return glyph

    if role == "text":
        parts = name.split()
        if parts:
            tail = parts[-1]
            if tail.replace(".", "", 1).replace(",", "", 1).replace("-", "", 1).isdigit():
                return tail
        if value and len(value) <= 16:
            return value
        if name and len(name) <= 12:
            return name

    if name and len(name) <= 4:
        return name

    if value and len(value) <= 4:
        return value

    if name:
        first = name.split()[0]
        if len(first) <= 5:
            return first

    if aid:
        token = _aid_token(aid)
        if token and len(token) <= 6:
            return token
        return aid[:8]

    return (elem.get("role") or "?")[:6]


def _percent_from_elem(elem: dict[str, Any]) -> Optional[float]:
    raw_min, raw_max, raw_now = elem.get("value_min"), elem.get("value_max"), elem.get("value_now")
    if raw_now is not None and raw_min is not None and raw_max is not None:
        try:
            vmin, vmax, vnow = float(raw_min), float(raw_max), float(raw_now)
            if vmax > vmin:
                return max(0.0, min(1.0, (vnow - vmin) / (vmax - vmin)))
        except (TypeError, ValueError):
            pass
    v = (elem.get("value") or "").strip()
    if not v:
        return None
    try:
        if v.endswith("%"):
            return max(0.0, min(1.0, float(v[:-1].strip()) / 100.0))
        if " of " in v.lower():
            n, d = v.lower().split(" of ", 1)
            return max(0.0, min(1.0, float(n.strip()) / float(d.strip())))
        f = float(v)
        if 0.0 <= f <= 1.0:
            return f
        if 0.0 <= f <= 100.0:
            return f / 100.0
    except (TypeError, ValueError):
        return None
    return None


def _role_glyph_row(elem: dict[str, Any], inner_w: int) -> Optional[str]:
    r = _norm_role(elem.get("role") or "")
    name = _label_for(elem)
    selected = bool(elem.get("selected") or elem.get("has_focus"))
    expanded = bool(elem.get("expanded"))
    value = (elem.get("value") or "").strip()
    enabled = elem.get("enabled", True)

    if r in ("checkbox", "togglebutton", "switch"):
        mark = "x" if selected else " "
        return (f"[{mark}] {name}" if name else f"[{mark}]")[:inner_w]
    if r in ("radiobutton", "radio"):
        mark = "•" if selected else " "
        return (f"({mark}) {name}" if name else f"({mark})")[:inner_w]
    if r in ("combobox", "dropdownbutton", "popupbutton"):
        arrow = "▼" if expanded else "▶"
        body = f"{arrow} {name}" if name else arrow
        if value:
            body = f"{body} [{value}]"
        return body[:inner_w]
    if r == "menuitem":
        return (("▸ " if expanded else "") + name).strip()[:inner_w]
    if r in ("slider", "scrollbar", "progressbar"):
        frac = _percent_from_elem(elem)
        if frac is not None and inner_w >= 6:
            bar_w = max(2, min(inner_w - 4, 12))
            filled = int(round(frac * bar_w))
            bar = ("▓" * filled) + ("░" * (bar_w - filled))
            return f"{bar} {int(round(frac * 100))}%"[:inner_w]
        return name[:inner_w] if name else None
    if r in ("edit", "textfield", "editabletext"):
        return f"_{value or name}_"[:inner_w]
    if r == "button":
        return _compact_label(elem)[:inner_w] or None
    if r == "text":
        return _compact_label(elem)[:inner_w] or None
    if not enabled and name:
        return f"({name})"[:inner_w]
    return name[:inner_w] if name else None


_UWP_CHROME_AIDS = frozenset(
    {
        "AppName",
        "Header",
        "TogglePaneButton",
        "NormalAlwaysOnTopButton",
        "Minimize",
        "Maximize",
        "Close",
        "CloseButton",
    }
)

_ANSI_RESET = "\033[0m"
_ANSI_KEY = "\033[36m"
_ANSI_FOCUS = "\033[91m"
_ANSI_BY_ROLE: dict[str, str] = {
    "Button": "\033[94m",
    "Text": "\033[92m",
    "Edit": "\033[93m",
    "ComboBox": "\033[95m",
    "ListItem": "\033[90m",
    "CheckBox": "\033[96m",
    "RadioButton": "\033[96m",
    "Hyperlink": "\033[34m",
    "DataItem": "\033[35m",
}
_ANSI_BG_BUTTON = "\033[48;5;24m"
_ANSI_FG_BUTTON = "\033[97m"
_ANSI_BG_OPERATOR = "\033[48;5;60m"
_ANSI_BG_TEXT = "\033[48;5;236m"
_ANSI_FG_TEXT = "\033[92m"
_ANSI_BG_MEMORY = "\033[48;5;238m"
_ANSI_FG_MEMORY = "\033[37m"
_FILL_BUTTON = "░"
_FILL_OPERATOR = "▒"
_FILL_TEXT = " "
_FILL_MEMORY = "░"


def _role_ansi(role: str) -> str:
    return _ANSI_BY_ROLE.get((role or "").strip(), "\033[37m")


def _center_inside(outer: dict[str, Any], inner: dict[str, Any], tol: int = 2) -> bool:
    ox, oy = int(outer.get("x") or 0), int(outer.get("y") or 0)
    ow, oh = int(outer.get("width") or 0), int(outer.get("height") or 0)
    ix, iy = int(inner.get("x") or 0), int(inner.get("y") or 0)
    iw, ih = int(inner.get("width") or 0), int(inner.get("height") or 0)
    if iw <= 0 or ih <= 0:
        return False
    cx, cy = ix + iw // 2, iy + ih // 2
    return (ox - tol) <= cx <= (ox + ow + tol) and (oy - tol) <= cy <= (oy + oh + tol)


def _is_wide_text_strip(elem: dict[str, Any], win_w: int) -> bool:
    if (elem.get("role") or "").strip() != "Text":
        return False
    w = int(elem.get("width") or 0)
    return win_w > 0 and w >= int(win_w * 0.35)


def _is_horizontal_chrome(elem: dict[str, Any], median_w: int, median_h: int) -> bool:
    w = int(elem.get("width") or 0)
    h = int(elem.get("height") or 0)
    if w <= 0 or h <= 0 or median_w <= 0 or median_h <= 0:
        return False
    aspect = w / h
    if aspect >= 2.6 and w >= int(median_w * 0.85):
        return True
    return w >= int(median_w * 2.0) and h <= int(median_h * 0.55)


def _cell_style(elem: dict[str, Any]) -> tuple[str, str, str]:
    """Return (bg, fg, fill_char) for a control."""
    role = (elem.get("role") or "").strip()
    aid = (elem.get("automation_id") or "").lower()
    if role == "Text":
        return _ANSI_BG_TEXT, _ANSI_FG_TEXT, "─"
    if "equal" in aid:
        return _ANSI_BG_OPERATOR, _ANSI_FG_BUTTON, "█"
    if any(k in aid for k in ("mem", "memory", "clearmemory")):
        return _ANSI_BG_MEMORY, _ANSI_FG_MEMORY, _FILL_MEMORY
    if any(
        k in aid
        for k in (
            "plus", "minus", "multiply", "divide", "percent",
            "negate", "invert", "xpower", "squareroot", "backspace",
        )
    ):
        return _ANSI_BG_OPERATOR, _ANSI_FG_BUTTON, _FILL_OPERATOR
    if role == "Button":
        return _ANSI_BG_BUTTON, _ANSI_FG_BUTTON, _FILL_BUTTON
    return "", _role_ansi(role), " "


def _split_band_by_spatial_clusters(
    band: list[tuple[dict[str, Any], float, float]],
    *,
    median_w: int,
) -> list[list[tuple[dict[str, Any], float, float]]]:
    """Split a Y-band into separate ASCII rows by width and horizontal gaps.

    Wide controls (nav strips, banners) get their own row instead of sitting
    between tighter neighbours. Remaining peers split when bbox gap exceeds threshold.
    """
    wide_thresh = max(120, int(median_w * 2.2))
    gap_thresh = max(16, int(median_w * 0.65))
    rows: list[list[tuple[dict[str, Any], float, float]]] = []
    peers: list[tuple[dict[str, Any], float, float]] = []

    for elem, cx, cy in band:
        w = int(elem.get("width") or 0)
        if w >= wide_thresh:
            rows.append([(elem, cx, cy)])
        else:
            peers.append((elem, cx, cy))

    if not peers:
        return rows

    peers.sort(key=lambda t: int(t[0].get("x") or 0))
    cluster: list[tuple[dict[str, Any], float, float]] = [peers[0]]
    for item in peers[1:]:
        prev = cluster[-1][0]
        prev_right = int(prev.get("x") or 0) + int(prev.get("width") or 0)
        left = int(item[0].get("x") or 0)
        if left - prev_right > gap_thresh:
            rows.append(cluster)
            cluster = [item]
        else:
            cluster.append(item)
    rows.append(cluster)
    return rows


def filter_elements_for_ascii(
    elements: list[dict[str, Any]],
    origin_x: int,
    origin_y: int,
    win_w: int,
    win_h: int,
    min_pixels: int = 6,
    max_area_ratio: float = 0.92,
    basic_only: bool = True,
) -> list[dict[str, Any]]:
    """Keep visible controls inside the window frame (pre-tree spatial filter)."""
    if win_w <= 0 or win_h <= 0:
        return []
    win_area = win_w * win_h
    kept: list[dict[str, Any]] = []
    for elem in elements:
        role = (elem.get("role") or "").strip()
        w = int(elem.get("width") or 0)
        h = int(elem.get("height") or 0)
        if w < min_pixels or h < min_pixels:
            continue
        x, y = int(elem.get("x") or 0), int(elem.get("y") or 0)
        cx, cy = x + w // 2, y + h // 2
        if not (origin_x <= cx <= origin_x + win_w and origin_y <= cy <= origin_y + win_h):
            continue
        area = w * h
        if win_area > 0 and area / win_area > max_area_ratio:
            continue
        name = (elem.get("name") or "").strip()
        aid = (elem.get("automation_id") or "").strip()
        if basic_only and aid in _UWP_CHROME_AIDS:
            continue
        if role in _SKIP_ROLES and not name and not aid:
            continue
        if role == "Window" and area / max(win_area, 1) > 0.5:
            continue
        if basic_only and role not in _BASIC_ROLES:
            continue
        if not basic_only and role not in _INTERACTIVE_ROLES and role not in _SKIP_ROLES:
            if not name and not aid:
                continue
        kept.append(elem)

    if len(kept) >= 4:
        widths = [int(e.get("width") or 0) for e in kept if int(e.get("width") or 0) > 0]
        heights = [int(e.get("height") or 0) for e in kept if int(e.get("height") or 0) > 0]
        median_w = _median_int(widths)
        median_h = _median_int(heights)
        kept = [
            e for e in kept
            if not _is_horizontal_chrome(e, median_w, median_h)
        ]

    return kept


def select_elements_for_ascii_render(
    elements: list[dict[str, Any]],
    origin_x: int,
    origin_y: int,
    win_w: int,
    win_h: int,
    min_pixels: int = 6,
    max_area_ratio: float = 0.92,
    basic_only: bool = True,
    occlusion_prune: bool = True,
) -> list[dict[str, Any]]:
    """Filter spatially, then build containment tree + occlusion (Phase B)."""
    filtered = filter_elements_for_ascii(
        elements, origin_x, origin_y, win_w, win_h, min_pixels, max_area_ratio, basic_only
    )
    roles = _BASIC_ROLES if basic_only else _INTERACTIVE_ROLES
    drawables = prepare_elements_for_render(filtered, roles, occlusion_prune=occlusion_prune)
    if not drawables:
        return drawables

    seen = {_elem_key(e) for e in drawables}
    _interactive = frozenset(
        {"Button", "Edit", "ComboBox", "CheckBox", "RadioButton", "Hyperlink", "ListItem", "DataItem"}
    )
    for elem in filtered:
        if _elem_key(elem) in seen:
            continue
        if _is_wide_text_strip(elem, win_w):
            if any(
                _center_inside(elem, d) and (d.get("role") or "").strip() in _interactive
                for d in drawables
            ):
                continue
            drawables = [
                d for d in drawables
                if not _center_inside(elem, d) or _is_wide_text_strip(d, win_w)
            ]
            drawables.append(elem)
            seen.add(_elem_key(elem))

    drawables.sort(key=lambda e: int(e.get("width") or 0) * int(e.get("height") or 0))
    return drawables


def _assign_element_metadata(
    elements: list[dict[str, Any]],
    focused: Optional[dict[str, Any]] = None,
) -> dict[tuple, dict[str, Any]]:
    meta: dict[tuple, dict[str, Any]] = {}
    tab_order = sorted(elements, key=lambda e: (int(e.get("y") or 0), int(e.get("x") or 0)))
    tab_counter = 0
    for idx, elem in enumerate(tab_order):
        tab_idx: Optional[int] = None
        if _is_focusable(elem):
            tab_counter += 1
            tab_idx = tab_counter
        is_focused = bool(focused and _elem_key(elem) == _elem_key(focused))
        meta[_elem_key(elem)] = {
            "key": _legend_key(idx),
            "tab_index": tab_idx,
            "focused": is_focused,
        }
    return meta


def _put_force(grid: list[list[str]], gx: int, gy: int, ch: str) -> None:
    if 0 <= gy < len(grid) and 0 <= gx < len(grid[0]) and ch:
        grid[gy][gx] = ch


def _clamp_rect(
    grid: list[list[str]], x1: int, y1: int, x2: int, y2: int
) -> tuple[int, int, int, int]:
    max_x = len(grid[0]) - 1 if grid else 0
    max_y = len(grid) - 1 if grid else 0
    x1 = max(1, min(max_x - 1, x1))
    y1 = max(1, min(max_y - 1, y1))
    x2 = max(x1 + 1, min(max_x, x2))
    y2 = max(y1 + 1, min(max_y, y2))
    return x1, y1, x2, y2


def _draw_rect(
    grid: list[list[str]], x1: int, y1: int, x2: int, y2: int, box: dict[str, str]
) -> None:
    if x2 < x1 or y2 < y1:
        return
    x1, y1, x2, y2 = _clamp_rect(grid, x1, y1, x2, y2)
    _put_force(grid, x1, y1, box["tl"])
    _put_force(grid, x2, y1, box["tr"])
    _put_force(grid, x1, y2, box["bl"])
    _put_force(grid, x2, y2, box["br"])
    for x in range(x1 + 1, x2):
        if grid[y1][x] in (" ", box["h"]):
            _put_force(grid, x, y1, box["h"])
        if grid[y2][x] in (" ", box["h"]):
            _put_force(grid, x, y2, box["h"])
    for y in range(y1 + 1, y2):
        if grid[y][x1] in (" ", box["v"]):
            _put_force(grid, x1, y, box["v"])
        if grid[y][x2] in (" ", box["v"]):
            _put_force(grid, x2, y, box["v"])


# Monospace cells are taller than wide on screen (~2:1 height:width).
_DEFAULT_CHAR_ASPECT = 2.0


def _median_int(values: list[int]) -> int:
    if not values:
        return 32
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


def _cell_outer_width(label: str, *, max_w: int = 8, min_w: int = 4) -> int:
    """Grid columns spanned by a boxed control (borders + short label)."""
    n = len((label or "").strip()) or 1
    return max(min_w, min(max_w, n + 2))


def _dedupe_row_peers(
    group: list[tuple[dict[str, Any], float, float]],
) -> list[tuple[dict[str, Any], float, float]]:
    """Drop UIA duplicates: same compact label and overlapping horizontal bboxes."""
    if len(group) < 2:
        return group
    ordered = sorted(group, key=lambda t: int(t[0].get("x") or 0))
    kept: list[tuple[dict[str, Any], float, float]] = []
    for item in ordered:
        elem, _cx, _cy = item
        label = _compact_label(elem)
        ex = int(elem.get("x") or 0)
        ew = int(elem.get("width") or 0)
        area = ew * int(elem.get("height") or 0)
        replace_idx: Optional[int] = None
        for i, (prev, _, _) in enumerate(kept):
            if _compact_label(prev) != label:
                continue
            px = int(prev.get("x") or 0)
            pw = int(prev.get("width") or 0)
            overlap = min(ex + ew, px + pw) - max(ex, px)
            if overlap <= 0:
                continue
            smaller = min(ew, pw) or 1
            if overlap / smaller < 0.35:
                continue
            prev_area = pw * int(prev.get("height") or 0)
            if area > prev_area:
                replace_idx = i
            else:
                replace_idx = -1
            break
        if replace_idx is None:
            kept.append(item)
        elif replace_idx >= 0:
            kept[replace_idx] = item
    return kept


def _pack_row_tight(
    group: list[tuple[dict[str, Any], float, float]],
    gy: int,
    row_h: int,
    inner_cols: int,
    *,
    max_cell_w: int = 8,
    gap: int = 1,
) -> list[tuple[dict[str, Any], int, int, int, int]]:
    """Pack row controls side-by-side, centered as a block."""
    ordered = sorted(group, key=lambda t: float(t[1]))
    specs: list[tuple[dict[str, Any], int]] = []
    for elem, _cx, _cy in ordered:
        label = _compact_label(elem)
        specs.append((elem, _cell_outer_width(label, max_w=max_cell_w)))
    total = sum(cw for _, cw in specs) + gap * max(0, len(specs) - 1)
    gx = max(1, (inner_cols - total) // 2)
    placements: list[tuple[dict[str, Any], int, int, int, int]] = []
    for elem, cw in specs:
        gx2 = min(inner_cols, gx + cw - 1)
        placements.append((elem, gx, gy, gx2, gy + row_h - 1))
        gx = gx2 + 1 + gap
    return placements


def _split_wide_only(
    band: list[tuple[dict[str, Any], float, float]],
    *,
    median_w: int,
) -> list[list[tuple[dict[str, Any], float, float]]]:
    """Put very wide controls on their own row; keep same-Y peers together."""
    wide_thresh = max(120, int(median_w * 2.2))
    rows: list[list[tuple[dict[str, Any], float, float]]] = []
    peers: list[tuple[dict[str, Any], float, float]] = []
    for elem, cx, cy in band:
        w = int(elem.get("width") or 0)
        if w >= wide_thresh:
            rows.append([(elem, cx, cy)])
        else:
            peers.append((elem, cx, cy))
    if peers:
        peers.sort(key=lambda t: int(t[0].get("x") or 0))
        rows.append(peers)
    return rows


def _resolve_row_overlaps(
    placements: list[tuple[dict[str, Any], int, int, int, int]],
    inner_cols: int,
) -> list[tuple[dict[str, Any], int, int, int, int]]:
    """Shift cells right to avoid horizontal overlap."""
    if not placements:
        return placements
    ordered = sorted(placements, key=lambda p: p[1])
    resolved: list[tuple[dict[str, Any], int, int, int, int]] = []
    for elem, gx1, gy1, gx2, gy2 in ordered:
        if resolved and gx1 <= resolved[-1][3]:
            gx1 = resolved[-1][3] + 1
            gx2 = gx1 + (gx2 - gx1)
        if gx2 > inner_cols:
            shift = gx2 - inner_cols
            gx1 = max(1, gx1 - shift)
            gx2 = max(gx1 + 2, gx2 - shift)
        resolved.append((elem, gx1, gy1, gx2, gy2))
    return resolved


def compute_compact_cell_layout(
    elements: list[dict[str, Any]],
    inner_cols: int,
    inner_rows: int,
    origin_x: int = 0,
    origin_y: int = 0,
    win_w: int = 0,
    *,
    cell_h: int = 3,
    max_cell_w: int = 8,
) -> tuple[dict[tuple, tuple[int, int, int, int]], dict[str, Any]]:
    """Compact row layout: small boxes sized to labels, X proportional within each row."""
    usable = [
        e for e in elements
        if int(e.get("width") or 0) > 0 and int(e.get("height") or 0) > 0
    ]
    meta: dict[str, Any] = {
        "mode": "legible",
        "layout": "compact",
        "rows": 0,
        "cols": 0,
        "cell_h": cell_h,
    }
    if not usable:
        return {}, meta

    items: list[tuple[dict[str, Any], float, float]] = []
    heights: list[int] = []
    for elem in usable:
        x = int(elem.get("x") or 0)
        y = int(elem.get("y") or 0)
        w = int(elem.get("width") or 0)
        h = int(elem.get("height") or 0)
        items.append((elem, x + w / 2.0, y + h / 2.0))
        heights.append(h)

    thresh = max(12, int(_median_int(heights) * 0.55))
    row_groups: list[list[tuple[dict[str, Any], float, float]]] = []
    for elem, cx, cy in sorted(items, key=lambda t: (t[2], t[1])):
        for group in row_groups:
            if abs(cy - group[0][2]) <= thresh:
                group.append((elem, cx, cy))
                break
        else:
            row_groups.append([(elem, cx, cy)])

    row_groups.sort(key=lambda g: g[0][2])
    median_w = _median_int([int(e.get("width") or 0) for e in usable])
    refined: list[list[tuple[dict[str, Any], float, float]]] = []
    for group in row_groups:
        refined.extend(_split_wide_only(group, median_w=median_w))
    row_groups = sorted(refined, key=lambda g: g[0][2])

    n_rows = len(row_groups)
    row_h = 3
    if n_rows * row_h > inner_rows:
        row_h = max(3, inner_rows // max(n_rows, 1))

    layout: dict[tuple, tuple[int, int, int, int]] = {}
    gy = 2
    max_cols = 0

    for group in row_groups:
        if not group:
            continue
        group = _dedupe_row_peers(group)
        wide_strip = [
            t for t in group
            if _is_wide_text_strip(t[0], win_w or int(t[0].get("width") or 0) * 2)
        ]
        if wide_strip:
            elem = wide_strip[0][0]
            label = _compact_label(elem)
            cw = min(inner_cols - 1, max(10, len(label) + 4))
            gx1 = 1 + max(0, (inner_cols - cw) // 2)
            gx2 = min(inner_cols, gx1 + cw - 1)
            layout[_elem_key(elem)] = (gx1, gy, gx2, gy + row_h - 1)
            max_cols = max(max_cols, 1)
            gy += row_h
            group = [t for t in group if t[0] is not elem]
            if not group:
                continue

        placements = _pack_row_tight(
            group, gy, row_h, inner_cols, max_cell_w=max_cell_w,
        )

        for elem, gx1, gy1, gx2, gy2 in _resolve_row_overlaps(placements, inner_cols):
            layout[_elem_key(elem)] = (gx1, gy1, gx2, gy2)
            max_cols = max(max_cols, gx2 - gx1 + 1)
        gy += row_h

    meta.update({"rows": n_rows, "cols": max_cols, "cell_h": row_h})
    return layout, meta


def compute_legible_cell_layout(
    elements: list[dict[str, Any]],
    inner_cols: int,
    inner_rows: int,
    *,
    min_cell_w: int = 5,
    min_cell_h: int = 3,
) -> tuple[dict[tuple, tuple[int, int, int, int]], dict[str, Any]]:
    """Legacy uniform grid (prefer compute_compact_cell_layout)."""
    usable = [
        e for e in elements
        if int(e.get("width") or 0) > 0 and int(e.get("height") or 0) > 0
    ]
    meta: dict[str, Any] = {
        "mode": "legible",
        "rows": 0,
        "cols": 0,
        "cell_w": 0,
        "cell_h": 0,
    }
    if not usable:
        return {}, meta

    items: list[tuple[dict[str, Any], float, float]] = []
    heights: list[int] = []
    for elem in usable:
        x = int(elem.get("x") or 0)
        y = int(elem.get("y") or 0)
        w = int(elem.get("width") or 0)
        h = int(elem.get("height") or 0)
        items.append((elem, x + w / 2.0, y + h / 2.0))
        heights.append(h)

    thresh = max(12, int(_median_int(heights) * 0.55))
    sorted_items = sorted(items, key=lambda t: (t[2], t[1]))
    row_groups: list[list[tuple[dict[str, Any], float, float]]] = []
    for elem, cx, cy in sorted_items:
        for group in row_groups:
            if abs(cy - group[0][2]) <= thresh:
                group.append((elem, cx, cy))
                break
        else:
            row_groups.append([(elem, cx, cy)])

    row_groups.sort(key=lambda g: g[0][2])
    median_w = _median_int([int(e.get("width") or 0) for e in usable])
    refined: list[list[tuple[dict[str, Any], float, float]]] = []
    for group in row_groups:
        refined.extend(_split_band_by_spatial_clusters(group, median_w=median_w))
    row_groups = sorted(refined, key=lambda g: g[0][2])
    for group in row_groups:
        group.sort(key=lambda t: int(t[0].get("x") or 0))

    n_rows = len(row_groups)
    max_cols = max(len(g) for g in row_groups)
    cell_h = max(min_cell_h, inner_rows // max(n_rows, 1))
    cell_w = max(min_cell_w, inner_cols // max(max_cols, 1))
    if n_rows * cell_h > inner_rows:
        cell_h = max(min_cell_h, inner_rows // n_rows)
    if max_cols * cell_w > inner_cols:
        cell_w = max(min_cell_w, inner_cols // max_cols)

    block_w = max_cols * cell_w
    block_h = n_rows * cell_h
    base_x = 1 + max(0, (inner_cols - block_w) // 2)
    base_y = 1 + max(0, (inner_rows - block_h) // 2)

    layout: dict[tuple, tuple[int, int, int, int]] = {}
    for row_idx, group in enumerate(row_groups):
        row_cols = len(group)
        row_w = row_cols * cell_w
        row_x = base_x + max(0, (block_w - row_w) // 2)
        for col_idx, (elem, _, _) in enumerate(group):
            gx1 = row_x + col_idx * cell_w
            gy1 = base_y + row_idx * cell_h
            gx2 = min(1 + inner_cols, gx1 + cell_w - 1)
            gy2 = min(1 + inner_rows, gy1 + cell_h - 1)
            layout[_elem_key(elem)] = (gx1, gy1, gx2, gy2)

    meta.update({"rows": n_rows, "cols": max_cols, "cell_w": cell_w, "cell_h": cell_h})
    return layout, meta


def compute_proportional_cell_layout(
    elements: list[dict[str, Any]],
    origin_x: int,
    origin_y: int,
    win_w: int,
    win_h: int,
    inner_cols: int,
    inner_rows: int,
    *,
    char_aspect: float = _DEFAULT_CHAR_ASPECT,
    min_cell_w: int = 3,
    min_cell_h: int = 2,
) -> tuple[dict[tuple, tuple[int, int, int, int]], dict[str, Any]]:
    """Map screen bboxes to grid cells preserving visual proportions."""
    viewport = compute_viewport_mapping(
        win_w,
        win_h,
        inner_cols,
        inner_rows,
        preserve_aspect=True,
        char_aspect=char_aspect,
    )
    scale = float(viewport["scale"])
    off_x = float(viewport["offset_gx"])
    off_y = float(viewport["offset_gy"])
    layout: dict[tuple, tuple[int, int, int, int]] = {}

    for elem in elements:
        x = int(elem.get("x") or 0)
        y = int(elem.get("y") or 0)
        w = int(elem.get("width") or 0)
        h = int(elem.get("height") or 0)
        if w <= 0 or h <= 0:
            continue
        gx1 = int(round((x - origin_x) * scale + off_x))
        gy1 = int(round((y - origin_y) * scale / max(char_aspect, 1.0) + off_y))
        gx2 = int(round((x + w - origin_x) * scale + off_x))
        gy2 = int(round((y + h - origin_y) * scale / max(char_aspect, 1.0) + off_y))
        gx1 = max(1, min(inner_cols, gx1))
        gy1 = max(1, min(inner_rows, gy1))
        gx2 = max(gx1 + min_cell_w, min(1 + inner_cols, gx2))
        gy2 = max(gy1 + min_cell_h, min(1 + inner_rows, gy2))
        if gx2 <= gx1:
            gx2 = min(1 + inner_cols, gx1 + min_cell_w)
        if gy2 <= gy1:
            gy2 = min(1 + inner_rows, gy1 + min_cell_h)
        layout[_elem_key(elem)] = (gx1, gy1, gx2, gy2)

    return layout, viewport


def _resolve_layout_mode(layout_mode: str, preserve_aspect: bool) -> str:
    mode = (layout_mode or "").strip().lower()
    if mode in ("proportional", "legible", "stretch"):
        return mode
    return "proportional" if preserve_aspect else "stretch"


def compute_viewport_mapping(
    win_w: int,
    win_h: int,
    inner_cols: int,
    inner_rows: int,
    *,
    preserve_aspect: bool = True,
    char_aspect: float = _DEFAULT_CHAR_ASPECT,
) -> dict[str, float]:
    """Map window pixels into the inner grid (uniform scale + letterbox when preserving aspect)."""
    win_w = max(int(win_w), 1)
    win_h = max(int(win_h), 1)
    inner_cols = max(int(inner_cols), 1)
    inner_rows = max(int(inner_rows), 1)

    if not preserve_aspect:
        return {
            "mode": "stretch",
            "scale_x": inner_cols / win_w,
            "scale_y": inner_rows / win_h,
            "offset_gx": 1.0,
            "offset_gy": 1.0,
            "used_w": float(inner_cols),
            "used_h": float(inner_rows),
        }

    # Uniform scale with monospace char aspect (tall cells ≈ 2× wide on screen).
    eff_h = win_h / max(char_aspect, 1.0)
    scale = min(inner_cols / win_w, inner_rows / eff_h)
    used_w = win_w * scale
    used_h = eff_h * scale
    return {
        "mode": "proportional",
        "scale": scale,
        "scale_x": scale,
        "scale_y": scale / max(char_aspect, 1.0),
        "char_aspect": char_aspect,
        "offset_gx": 1.0 + max(0.0, (inner_cols - used_w) / 2.0),
        "offset_gy": 1.0 + max(0.0, (inner_rows - used_h) / 2.0),
        "used_w": used_w,
        "used_h": used_h,
    }


def _paint_cell_interior(
    grid: list[list[str]],
    gx1: int,
    gy1: int,
    gx2: int,
    gy2: int,
    label: str,
    *,
    use_colors: bool = False,
    bg: str = "",
    fg: str = "",
    fill_char: str = " ",
) -> None:
    inner_w = max(0, gx2 - gx1 - 1)
    inner_h = max(0, gy2 - gy1 - 1)
    if inner_w < 1 or inner_h < 1:
        return
    label = (label or "")[:inner_w]
    mid_y = gy1 + 1
    sx = gx1 + 1 + max(0, (inner_w - len(label)) // 2)
    shade = fill_char if fill_char else " "
    for yy in range(gy1 + 1, gy2):
        for xx in range(gx1 + 1, gx2):
            if grid[yy][xx] in _BORDER_CHARS:
                continue
            grid[yy][xx] = shade
    for i, ch in enumerate(label):
        x = sx + i
        if gx1 < x < gx2 and gy1 <= mid_y <= gy2:
            grid[mid_y][x] = ch


def _put_colored_text(
    grid: list[list[str]], gx: int, gy: int, text: str, color: str = ""
) -> None:
    for i, ch in enumerate(text):
        cx = gx + i
        if 0 <= gy < len(grid) and 0 <= cx < len(grid[0]) and grid[gy][cx] == " ":
            grid[gy][cx] = f"{color}{ch}{_ANSI_RESET}" if color else ch


def render_ascii_ui(
    elements: list[dict[str, Any]],
    origin_x: int,
    origin_y: int,
    win_w: int,
    win_h: int,
    cols: int = 80,
    height: int = 36,
    title: str = "",
    focused: Optional[dict[str, Any]] = None,
    unicode_box: bool = True,
    include_keys: bool = True,
    include_tab_index: bool = True,
    preserve_aspect: bool = True,
    layout_mode: str = "proportional",
    char_aspect: float = _DEFAULT_CHAR_ASPECT,
    use_colors: bool = False,
) -> dict[str, Any]:
    """Build ASCII map string, legend, and structured element records.

    layout_mode:
      proportional (default) — pixel bbox mapped with char-aspect correction
      legible — row/column grid that fills the map for dense UIs
      stretch — independent X/Y stretch to grid edges
    """
    cols = max(40, min(int(cols or 80), 140))
    rows = max(12, min(int(height or 36), 80))
    mode = _resolve_layout_mode(layout_mode, preserve_aspect)
    box = _UNICODE_BOX if unicode_box else _ASCII_BOX
    grid = [[" " for _ in range(cols)] for _ in range(rows)]

    _draw_rect(grid, 0, 0, cols - 1, rows - 1, box)
    header = (title or "UI").strip()
    if len(header) > cols - 4:
        header = header[: cols - 7] + "..."
    for i, ch in enumerate(f" {header} "[: cols - 2]):
        _put_force(grid, 1 + i, 0, ch)

    inner_cols, inner_rows = cols - 2, rows - 2
    meta_map = _assign_element_metadata(elements, focused=focused)
    structured: list[dict[str, Any]] = []

    cell_layout: dict[tuple, tuple[int, int, int, int]] = {}
    if mode == "legible":
        cell_layout, viewport = compute_compact_cell_layout(
            elements,
            inner_cols,
            inner_rows,
            origin_x,
            origin_y,
            win_w,
        )
    elif mode == "proportional":
        cell_layout, viewport = compute_proportional_cell_layout(
            elements,
            origin_x,
            origin_y,
            win_w,
            win_h,
            inner_cols,
            inner_rows,
            char_aspect=char_aspect,
        )
    else:
        viewport = compute_viewport_mapping(
            win_w,
            win_h,
            inner_cols,
            inner_rows,
            preserve_aspect=False,
            char_aspect=char_aspect,
        )

    def to_gx(px: int) -> int:
        gxf = (px - origin_x) * viewport["scale_x"] + viewport["offset_gx"]
        return max(1, min(cols - 2, int(round(gxf))))

    def to_gy(py: int) -> int:
        gyf = (py - origin_y) * viewport["scale_y"] + viewport["offset_gy"]
        return max(1, min(rows - 2, int(round(gyf))))

    paint_jobs: list[dict[str, Any]] = []
    for elem in elements:
        x, y = int(elem.get("x") or 0), int(elem.get("y") or 0)
        w, h = int(elem.get("width") or 0), int(elem.get("height") or 0)
        if w <= 0 or h <= 0:
            continue

        if cell_layout:
            bounds = cell_layout.get(_elem_key(elem))
            if not bounds:
                continue
            gx1, gy1, gx2, gy2 = bounds
        else:
            gx1, gy1 = to_gx(x), to_gy(y)
            gx2, gy2 = to_gx(x + w), to_gy(y + h)
            gx2 = min(max(gx1 + 2, gx2), cols - 2)
            gy2 = min(max(gy1 + 2, gy2), rows - 2)
            if gx2 <= gx1:
                gx2 = min(cols - 2, gx1 + 1)
            if gy2 <= gy1:
                gy2 = min(rows - 2, gy1 + 1)

        em = meta_map.get(_elem_key(elem), {"key": "", "tab_index": None, "focused": False})
        inner_w, inner_h = gx2 - gx1 - 1, gy2 - gy1 - 1
        glyph_line = _role_glyph_row(elem, inner_w) if inner_w >= 1 else _compact_label(elem)
        if not glyph_line:
            glyph_line = _compact_label(elem)
        bg, fg, fill_char = _cell_style(elem)
        paint_jobs.append(
            {
                "elem": elem,
                "bounds": (gx1, gy1, gx2, gy2),
                "glyph": glyph_line,
                "bg": bg,
                "fg": fg,
                "fill": fill_char,
                "key": em.get("key") or "",
                "tab_idx": em.get("tab_index"),
                "focused": bool(em.get("focused")),
                "area": w * h,
            }
        )

    paint_jobs.sort(key=lambda j: j["area"], reverse=True)

    color_map: dict[tuple[int, int], tuple[str, str]] = {}
    for job in paint_jobs:
        gx1, gy1, gx2, gy2 = job["bounds"]
        _draw_rect(grid, gx1, gy1, gx2, gy2, box)

    for job in paint_jobs:
        gx1, gy1, gx2, gy2 = job["bounds"]
        _paint_cell_interior(
            grid, gx1, gy1, gx2, gy2, job["glyph"],
            fill_char=(" " if not use_colors else job["fill"]),
        )
        if use_colors and job["bg"]:
            for yy in range(gy1 + 1, gy2):
                for xx in range(gx1 + 1, gx2):
                    if (xx, yy) not in color_map:
                        color_map[(xx, yy)] = (job["bg"], job["fg"])

    for job in sorted(paint_jobs, key=lambda j: j["area"]):
        gx1, gy1, gx2, gy2 = job["bounds"]
        inner_w, inner_h = gx2 - gx1 - 1, gy2 - gy1 - 1
        elem = job["elem"]
        x, y = int(elem.get("x") or 0), int(elem.get("y") or 0)
        w, h = int(elem.get("width") or 0), int(elem.get("height") or 0)

        if include_tab_index and job["tab_idx"] is not None and inner_h >= 2:
            _put_colored_text(grid, gx1 + 1, gy1 + 1, _tab_glyph(int(job["tab_idx"])), "")

        if include_keys and job["key"] and inner_w >= len(job["key"]) + 1:
            _put_colored_text(grid, gx2 - len(job["key"]), gy1 + 1, job["key"], "")

        if job["focused"] and inner_w >= 1 and inner_h >= 1:
            fx = min(gx2 - 1, gx1 + inner_w // 2)
            fy = min(gy2 - 1, gy1 + max(1, inner_h // 2))
            if grid[fy][fx] not in _BORDER_CHARS:
                grid[fy][fx] = "@"

        structured.append(
            {
                "key": job["key"],
                "tab_index": job["tab_idx"],
                "role": (elem.get("role") or "").strip(),
                "name": (elem.get("name") or "").strip(),
                "automation_id": (elem.get("automation_id") or "").strip(),
                "focused": job["focused"],
                "grid_bounds": [gx1, gy1, gx2, gy2],
                "screen_bounds": [x, y, x + w, y + h],
                **({"value": str(elem.get("value"))} if elem.get("value") else {}),
                **({"ocr_enriched": True} if elem.get("ocr_enriched") else {}),
            }
        )

    if use_colors and color_map:
        for y in range(rows):
            row = grid[y]
            for x in range(cols):
                style = color_map.get((x, y))
                ch = row[x]
                if style and ch and ch not in _BORDER_CHARS:
                    bg, fg = style
                    row[x] = f"{bg}{fg}{ch}{_ANSI_RESET}"

    ascii_body = "\n".join("".join(row).rstrip() for row in grid).rstrip()
    legend_parts = ["Leyenda: eN=id accionable", "①②=tab", "@=foco", "[x]/▼/▓=rol"]
    if not unicode_box:
        legend_parts[1] = "#N=tab"
    legend = "  ".join(legend_parts)
    def _legend_entry(r: dict[str, Any]) -> str:
        base = (
            f"{r['key']}={r['role']}"
            + (f' "{r["name"][:16]}"' if r.get("name") else "")
            + (
                f" @{r['automation_id'][:12]}"
                if r.get("automation_id") and not r.get("name")
                else ""
            )
        )
        if not use_colors:
            return base
        return f"{_ANSI_KEY}{r['key']}{_ANSI_RESET}={_role_ansi(r.get('role') or '')}{r['role']}{_ANSI_RESET}" + (
            f' "{r["name"][:16]}"' if r.get("name") else ""
        ) + (
            f" @{r['automation_id'][:12]}"
            if r.get("automation_id") and not r.get("name")
            else ""
        )

    key_legend = "  ".join(_legend_entry(r) for r in structured[:14])
    if key_legend:
        legend = f"{legend}\n{key_legend}"

    return {
        "ascii": ascii_body,
        "legend": legend,
        "cols": cols,
        "rows": rows,
        "rendered_count": len(elements),
        "elements": structured,
        "viewport": viewport,
    }


def build_legend_lines() -> list[str]:
    return [
        "  e1,e2 = legend keys (use with click_element / automation_id)",
        "  ①②③ = tab order among focusable controls",
        "  @ = keyboard focus",
    ]

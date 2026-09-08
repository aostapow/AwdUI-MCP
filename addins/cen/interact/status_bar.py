"""Read COBIS status/help line hints from bottom of form."""
from __future__ import annotations

import json
from typing import Any, Optional


def read_status_hints(window_title: Optional[str] = None) -> dict[str, Any]:
    """Scan lower-band text for help line / transaction line patterns."""
    from tools.ui_automation import do_list_elements

    listed = do_list_elements(window_title=window_title or "", max_depth=4)
    if isinstance(listed, str):
        listed = json.loads(listed)

    elements = listed.get("elements") or []
    texts: list[dict[str, str]] = []
    for el in elements:
        name = (el.get("name") or "").strip()
        role = (el.get("role") or "").lower()
        if not name or len(name) < 3:
            continue
        if role in ("text", "statusbar", "pane", "group") or name.lower().startswith(
            ("lbl", "dl_", "status")
        ):
            texts.append({"name": name, "role": role})

    combined = " ".join(t["name"] for t in texts).lower()
    hints = {
        "help_line": any(k in combined for k in ("f5", "ayuda", "help", "catalogo")),
        "transaction_line": any(k in combined for k in ("transacc", "usuario", "oficina")),
        "validation": any(k in combined for k in ("obligatorio", "mandatorio", "error")),
    }

    return {
        "success": True,
        "resolved_window_title": listed.get("resolved_window_title") or window_title or "",
        "status_texts": texts[-12:],
        "hints": hints,
        "note": "ShowHelpLine/ShowTransactionLine render as COBISPanel/lbl near bottom",
    }

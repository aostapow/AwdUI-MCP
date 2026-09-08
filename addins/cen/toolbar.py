"""COBIS transactional toolbar (cmdBoton[]) helpers."""
from __future__ import annotations

import json
import re
from typing import Any, Optional

_DEFAULT_ACTIONS = {
    0: "Buscar",
    1: "Siguiente",
    2: "Limpiar",
    3: "Salir",
    4: "Imprimir",
}


def _caption_aliases(caption: str) -> list[str]:
    cap = (caption or "").strip().lower().replace("&", "")
    aliases = [cap]
    try:
        import json
        from pathlib import Path

        omap = json.loads(
            (Path(__file__).resolve().parent / "object_map.json").read_text(encoding="utf-8")
        )
        for _key, variants in (omap.get("toolbar") or {}).get("common_captions", {}).items():
            for v in variants:
                vnorm = v.lower().replace("&", "")
                if cap in vnorm or vnorm in cap or cap == _key:
                    aliases.extend(v.lower().replace("&", "") for v in variants)
    except Exception:
        pass
    return list(dict.fromkeys(aliases))


def resolve_toolbar_intent(
    intent: str,
    window_title: Optional[str] = None,
    form_id: str = "",
) -> dict[str, Any]:
    """Map intent (search/next/exit/transmit) to caption from live toolbar or catalog."""
    intent_key = (intent or "").strip().lower()
    if not intent_key:
        return {"success": False, "error": "intent required (search, next, clear, exit, transmit, create, delete, choose, print)"}

    from pathlib import Path

    omap: dict[str, Any] = {}
    try:
        omap = json.loads(
            (Path(__file__).resolve().parent / "object_map.json").read_text(encoding="utf-8")
        )
    except Exception:
        pass

    captions_map = (omap.get("toolbar") or {}).get("common_captions") or {}
    candidates = captions_map.get(intent_key, [intent_key.capitalize()])

    listed = list_cobis_toolbar(window_title)
    buttons = listed.get("buttons") or []
    for cap in candidates:
        for btn in buttons:
            bname = (btn.get("name") or "").lower().replace("&", "")
            cnorm = cap.lower().replace("&", "")
            if cnorm in bname or bname in cnorm:
                return {
                    "success": True,
                    "intent": intent_key,
                    "caption": btn.get("name"),
                    "button": btn,
                    "source": "live_toolbar",
                }

    if form_id:
        from detect.forms_catalog import get_form_profile

        prof = get_form_profile(form_id)
        if prof.get("success"):
            toolbar = prof["form"].get("toolbar") or {}
            for _idx, btn in toolbar.items():
                text = (btn.get("text") or "").replace("&", "")
                for cap in candidates:
                    if cap.lower().replace("&", "") in text.lower():
                        return {
                            "success": True,
                            "intent": intent_key,
                            "caption": btn.get("text"),
                            "button_index": _idx,
                            "tag": btn.get("tag"),
                            "source": "catalog",
                        }

    return {
        "success": False,
        "error": f"intent '{intent_key}' not resolved",
        "candidates": candidates,
        "live_buttons": [b.get("name") for b in buttons],
    }


def click_toolbar_intent(
    intent: str,
    window_title: Optional[str] = None,
    form_id: str = "",
) -> dict[str, Any]:
    """Resolve intent then click toolbar by caption."""
    resolved = resolve_toolbar_intent(intent, window_title, form_id)
    if not resolved.get("success"):
        return resolved
    cap = resolved.get("caption") or ""
    click = click_cobis_toolbar(caption=cap, window_title=window_title)
    return {**resolved, "click": click, "success": bool(click.get("success"))}


def list_cobis_toolbar(window_title: Optional[str] = None) -> dict[str, Any]:
    from tools.ui_automation import do_list_elements

    listed = do_list_elements(window_title=window_title or "", max_depth=5)
    if isinstance(listed, str):
        try:
            listed = json.loads(listed)
        except Exception:
            listed = {}

    elements = listed.get("elements") or []
    buttons: list[dict[str, Any]] = []
    for el in elements:
        aid = str(el.get("automation_id") or "")
        name = str(el.get("name") or "")
        blob = f"{aid} {name}".lower()
        if "cmdboton" not in blob and not re.search(r"_cmdboton_\d+", blob):
            continue
        idx_match = re.search(r"(\d+)\s*$", aid) or re.search(r"_(\d+)$", aid)
        idx = int(idx_match.group(1)) if idx_match else len(buttons)
        buttons.append(
            {
                "index": idx,
                "automation_id": aid,
                "name": name or _DEFAULT_ACTIONS.get(idx, f"cmdBoton[{idx}]"),
                "enabled": el.get("enabled", True),
                "visible": el.get("visible", True),
            }
        )

    buttons.sort(key=lambda b: b["index"])
    return {
        "success": True,
        "buttons": buttons,
        "count": len(buttons),
        "resolved_window_title": listed.get("resolved_window_title") or window_title or "",
    }


def click_cobis_toolbar(
    index: int = -1,
    caption: str = "",
    window_title: Optional[str] = None,
) -> dict[str, Any]:
    listed = list_cobis_toolbar(window_title)
    if not listed.get("success"):
        return listed
    buttons = listed.get("buttons") or []
    if not buttons:
        return {"success": False, "error": "No cmdBoton toolbar buttons found"}

    target: Optional[dict[str, Any]] = None
    cap = (caption or "").strip().lower().replace("&", "")
    if cap:
        aliases = _caption_aliases(caption)
        for btn in buttons:
            bname = (btn.get("name") or "").lower().replace("&", "")
            if any(a in bname or bname in a for a in aliases):
                target = btn
                break
    elif index >= 0:
        for btn in buttons:
            if btn.get("index") == index:
                target = btn
                break

    if target is None:
        return {"success": False, "error": "Toolbar button not found", "buttons": buttons}

    from tools.ui_automation import do_click_element

    aid = target.get("automation_id") or ""
    click = do_click_element(automation_id=aid, window_title=window_title or "")
    ok = isinstance(click, dict) and click.get("success")
    return {
        "success": bool(ok),
        "button": target,
        "click_result": click,
    }

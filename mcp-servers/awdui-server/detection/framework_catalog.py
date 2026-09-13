"""Framework + control catalog for Repo Studio and agents (read-only)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

_DATA_DIR = Path(__file__).resolve().parent / "data"
_UIA_MAP_PATH = _DATA_DIR / "uia_control_map.json"

# QTP Swf* method → MCP implementation (repo_action delegates to these)
REPO_METHOD_MCP: dict[str, dict[str, Any]] = {
    "Click": {
        "mcp_tools": ["repo_action", "invoke_element", "click_element"],
        "summary": "InvokePattern o click en bbox UIA",
    },
    "DblClick": {
        "mcp_tools": ["repo_action", "double_click_element"],
        "summary": "Doble click en centro del control",
    },
    "Set": {
        "mcp_tools": ["repo_action", "set_element_value"],
        "summary": "ValuePattern / texto en Edit o Combo editable",
    },
    "SetSecure": {
        "mcp_tools": ["repo_action", "set_element_value"],
        "summary": "Campo enmascarado (password)",
    },
    "Type": {
        "mcp_tools": ["repo_action", "type_into_element", "type_text"],
        "summary": "Teclado simulado en el control",
    },
    "Select": {
        "mcp_tools": ["repo_action", "select_control_item"],
        "summary": "SelectionItem en lista/combo/tab",
    },
    "Deselect": {
        "mcp_tools": ["repo_action", "select_control_item"],
        "summary": "Quitar selección en lista",
    },
    "Expand": {
        "mcp_tools": ["repo_action", "expand_element"],
        "summary": "ExpandCollapsePattern Expand",
    },
    "Collapse": {
        "mcp_tools": ["repo_action", "expand_collapse_element"],
        "summary": "ExpandCollapsePattern Collapse",
    },
    "GetROProperty": {
        "mcp_tools": ["repo_action", "get_element_properties", "read_element"],
        "summary": "Leer propiedad UIA en runtime",
    },
    "GetVisibleText": {
        "mcp_tools": ["repo_action", "read_element", "find_text"],
        "summary": "Texto visible (Value/name u OCR fallback)",
    },
    "GetItem": {
        "mcp_tools": ["repo_action", "list_control_items"],
        "summary": "Ítem de lista por índice/nombre",
    },
    "Highlight": {
        "mcp_tools": ["repo_action", "highlight_element"],
        "summary": "Overlay visual de depuración",
    },
    "FireEvent": {
        "mcp_tools": ["repo_action", "invoke_element"],
        "summary": "Evento UIA alternativo",
    },
    "SetSelection": {
        "mcp_tools": ["repo_action", "set_element_value"],
        "summary": "Selección de texto en Edit",
    },
}

_FRAMEWORK_LABELS: dict[str, str] = {
    "uwp": "UWP / WinUI",
    "win32": "Win32 nativo",
    "winforms": "WinForms (.NET)",
    "wpf": "WPF",
    "electron": "Electron / Chromium embebido",
    "chromium_browser": "Navegador Chromium",
    "java_swing": "Java Swing",
    "java_fx": "JavaFX",
    "qt": "Qt",
    "gtk": "GTK",
    "unknown": "Desconocido",
}

_SWF_FRAMEWORKS = frozenset({"winforms", "wpf", "win32"})


def _load_uia_map() -> dict[str, Any]:
    if not _UIA_MAP_PATH.is_file():
        return {}
    return json.loads(_UIA_MAP_PATH.read_text(encoding="utf-8"))


def _framework_entries() -> list[dict[str, Any]]:
    from tools.framework_detect import _FRAMEWORK_INFO

    out: list[dict[str, Any]] = []
    for fw_id, (uia_support, hints) in _FRAMEWORK_INFO.items():
        out.append({
            "id": fw_id,
            "label": _FRAMEWORK_LABELS.get(fw_id, fw_id),
            "uia_support": uia_support,
            "hints": list(hints),
            "uses_swf_repo": fw_id in _SWF_FRAMEWORKS,
        })
    out.sort(key=lambda x: x["label"])
    return out


def _swf_classes() -> list[dict[str, Any]]:
    from detection.winforms_map import SWF_PROFILES, SWF_TO_ROLE

    classes: list[dict[str, Any]] = []
    for swf_class, profile in sorted(SWF_PROFILES.items()):
        methods = []
        for name in profile.get("methods", []):
            meta = REPO_METHOD_MCP.get(name, {"mcp_tools": ["repo_action"], "summary": ""})
            methods.append({
                "name": name,
                "mcp_tools": meta.get("mcp_tools", ["repo_action"]),
                "summary": meta.get("summary", ""),
            })
        classes.append({
            "swf_class": swf_class,
            "uia_role": SWF_TO_ROLE.get(swf_class, ""),
            "mandatory": list(profile.get("mandatory", [])),
            "assistive": list(profile.get("assistive", [])),
            "smart": list(profile.get("smart", [])),
            "methods": methods,
        })
    return classes


def _uia_controls() -> list[dict[str, Any]]:
    raw = _load_uia_map()
    controls = raw.get("controls") or {}
    out: list[dict[str, Any]] = []
    for role, spec in sorted(controls.items()):
        act = spec.get("act") or []
        out.append({
            "role": role,
            "patterns_ms": spec.get("patterns_ms") or {},
            "read_tools": list(spec.get("read") or []),
            "act_bindings": [
                {
                    "id": a.get("id", ""),
                    "tools": list(a.get("tools") or []),
                    "patterns": list(a.get("patterns") or []),
                    "steps": list(a.get("steps") or []),
                }
                for a in act
            ],
            "fallback_tools": list(spec.get("fallback") or []),
        })
    return out


def stored_objects_summary(db_path: Optional[Path] = None) -> dict[str, Any]:
    """Aggregate captured repo objects by framework and Swf class."""
    from detection import repo_store

    by_framework: dict[str, dict[str, int]] = {}
    apps: list[dict[str, Any]] = []
    for app in repo_store.list_applications(db_path):
        fw = (app.get("framework") or "unknown").strip() or "unknown"
        app_name = app.get("app_name") or app.get("app_id") or ""
        exe = app.get("exe_path") or ""
        objs = repo_store.list_objects_for_app(app_name, exe, db_path=db_path)
        by_class: dict[str, int] = {}
        for obj in objs:
            cls = obj.get("class") or obj.get("swf_class") or "SwfObject"
            by_class[cls] = by_class.get(cls, 0) + 1
        if not by_class:
            continue
        by_framework.setdefault(fw, {})
        for cls, n in by_class.items():
            by_framework[fw][cls] = by_framework[fw].get(cls, 0) + n
        apps.append({
            "app_id": app.get("app_id"),
            "app_name": app_name,
            "framework": fw,
            "object_count": sum(by_class.values()),
            "by_class": by_class,
        })
    return {"by_framework": by_framework, "apps": apps}


def build_framework_catalog(include_stored: bool = True) -> dict[str, Any]:
    """Full catalog payload for Repo Studio / API."""
    uia_raw = _load_uia_map()
    catalog: dict[str, Any] = {
        "schema_version": 1,
        "source_uia_map": uia_raw.get("source_url", ""),
        "frameworks": _framework_entries(),
        "swf_classes": _swf_classes(),
        "uia_controls": _uia_controls(),
        "repo_method_reference": REPO_METHOD_MCP,
    }
    if include_stored:
        catalog["stored"] = stored_objects_summary()
    return catalog

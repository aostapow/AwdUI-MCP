"""Flow hint retrieval from static knowledge."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


@lru_cache(maxsize=1)
def _load_flows() -> dict[str, Any]:
    path = Path(__file__).resolve().parent / "knowledge" / "flows.json"
    return json.loads(path.read_text(encoding="utf-8"))


def get_flow_hint(flow_id: str = "consulta_estandar") -> dict[str, Any]:
    flows = _load_flows().get("flows", {})
    if flow_id not in flows:
        return {
            "success": False,
            "error": f"Unknown flow_id: {flow_id}",
            "available": sorted(flows.keys()),
        }
    return {"success": True, "flow_id": flow_id, **flows[flow_id]}


def list_flows() -> dict[str, Any]:
    flows = _load_flows().get("flows", {})
    return {
        "success": True,
        "flows": [
            {"id": fid, "description": f.get("description", "")}
            for fid, f in flows.items()
        ],
    }

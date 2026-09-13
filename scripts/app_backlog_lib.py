"""Canonical per-app work queue for MCP lab (single source of truth).

Paths:
  .cursor/mcp-improvement-cycle/apps/{slug}/backlog.json   — edit via API here only
  .cursor/mcp-improvement-cycle/apps/{slug}/backlog.md     — generated (read-only)
  .cursor/mcp-improvement-cycle/apps/{slug}/manifest.json  — active_run, framework
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
APPS_ROOT = REPO_ROOT / ".cursor" / "mcp-improvement-cycle" / "apps"
STATE_PATH = REPO_ROOT / ".cursor" / "mcp-improvement-cycle" / "state.json"
RUNS_ROOT = REPO_ROOT / ".cursor" / "mcp-improvement-cycle" / "runs"

BACKLOG_VERSION = 1
ITEM_STATUSES = frozenset(
    {"pending", "in_progress", "done", "blocked", "na", "cancelled"}
)
FLOW_STATUS_TO_BACKLOG = {
    "met": "done",
    "pending": "pending",
    "exploring": "in_progress",
    "partial": "pending",
    "blocked": "blocked",
    "cancelled": "cancelled",
}


def slug_from_app_name(app_name: str) -> str:
    raw = (app_name or "").strip().lower()
    raw = raw.split(" - ")[0].split("|")[0].strip()
    safe = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return safe or "app"


def app_dir(slug: str) -> Path:
    return APPS_ROOT / slug


def backlog_json_path(slug: str) -> Path:
    return app_dir(slug) / "backlog.json"


def backlog_md_path(slug: str) -> Path:
    return app_dir(slug) / "backlog.md"


def manifest_path(slug: str) -> Path:
    return app_dir(slug) / "manifest.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _priority_int(value: Any, default: int = 99) -> int:
    """priority 0 is valid — do not use `value or default`."""
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _new_run_id(slug: str) -> str:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{slug}-{day}"


def default_hygiene_items() -> list[dict[str, Any]]:
    """Fase 0 — siempre al crear backlog nuevo."""
    return [
        {
            "id": "W-H01",
            "category": "hygiene",
            "status": "pending",
            "title": "Fase 0: launch_app + focus_window + set_target_window",
            "success_criteria": "Calculadora visible; target hwnd pinneado; discovered.yaml actualizado",
            "notes": "launch_app (replace si duda) → focus → set_target disambiguate=foreground",
            "ref": "phase0",
            "source": "catalog",
            "priority": 0,
            "parent_id": None,
            "evidence": [],
        },
        {
            "id": "W-H02",
            "category": "hygiene",
            "status": "pending",
            "title": "Fase 0: detect_framework + detection_health",
            "success_criteria": "framework y process en discovered.yaml; detection_health OK",
            "notes": "window_title explícito si no está foreground",
            "ref": "phase0",
            "source": "catalog",
            "priority": 1,
            "parent_id": None,
            "evidence": [],
        },
    ]


def compute_progress(items: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(items)
    pending = sum(1 for i in items if i.get("status") == "pending")
    in_progress = sum(1 for i in items if i.get("status") == "in_progress")
    done = sum(1 for i in items if i.get("status") == "done")
    blocked = sum(1 for i in items if i.get("status") == "blocked")
    na = sum(1 for i in items if i.get("status") == "na")
    cancelled = sum(1 for i in items if i.get("status") == "cancelled")
    open_items = pending + in_progress + blocked
    complete = total > 0 and open_items == 0
    return {
        "total": total,
        "pending": pending,
        "in_progress": in_progress,
        "done": done,
        "blocked": blocked,
        "na": na,
        "cancelled": cancelled,
        "complete": complete,
    }


def _parent_done(items: list[dict[str, Any]], item: dict[str, Any]) -> bool:
    pid = item.get("parent_id")
    if not pid:
        return True
    by_id = {str(i.get("id")): i for i in items if i.get("id")}
    parent = by_id.get(str(pid))
    if not parent:
        return True
    return parent.get("status") == "done"


def next_pending_item(backlog: dict[str, Any]) -> Optional[dict[str, Any]]:
    items = backlog.get("items") or []
    candidates = [
        i
        for i in items
        if i.get("status") in ("pending", "in_progress")
        and _parent_done(items, i)
    ]
    if not candidates:
        return None

    def sort_key(i: dict) -> tuple:
        cat = i.get("category") or "flow"
        cat_rank = {"hygiene": 0, "flow": 1, "tool": 2, "gate": 3}.get(cat, 9)
        return (cat_rank, _priority_int(i.get("priority")), str(i.get("id") or ""))

    return sorted(candidates, key=sort_key)[0]


def load_backlog(slug: str) -> Optional[dict[str, Any]]:
    path = backlog_json_path(slug)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_backlog(slug: str, backlog: dict[str, Any]) -> Path:
    backlog["updated_at"] = _now_iso()
    backlog["progress"] = compute_progress(backlog.get("items") or [])
    nxt = next_pending_item(backlog)
    backlog["next_item_id"] = nxt.get("id") if nxt else None
    d = app_dir(slug)
    d.mkdir(parents=True, exist_ok=True)
    path = backlog_json_path(slug)
    path.write_text(json.dumps(backlog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load_manifest(slug: str) -> dict[str, Any]:
    path = manifest_path(slug)
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_manifest(slug: str, manifest: dict[str, Any]) -> None:
    manifest["updated_at"] = _now_iso()
    app_dir(slug).mkdir(parents=True, exist_ok=True)
    manifest_path(slug).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def flow_to_backlog_item(flow: dict[str, Any], *, run_id: str) -> dict[str, Any]:
    fid = str(flow.get("id") or "")
    wid = f"W-{fid}" if fid.startswith("F-") else f"W-F-{fid}"
    st = FLOW_STATUS_TO_BACKLOG.get(str(flow.get("status") or "pending"), "pending")
    parent = flow.get("parent_id")
    parent_wid = f"W-{parent}" if parent and str(parent).startswith("F-") else parent
    evidence = []
    if flow.get("evidence_ref"):
        evidence.append(str(flow["evidence_ref"]))
    return {
        "id": wid,
        "category": "flow",
        "status": st,
        "title": flow.get("title") or fid,
        "success_criteria": flow.get("success_criteria") or "",
        "notes": flow.get("notes") or flow.get("repo_hints_note") or "",
        "ref": fid,
        "source": flow.get("source") or "imported",
        "priority": _priority_int(flow.get("priority")),
        "parent_id": parent_wid,
        "kind": flow.get("kind"),
        "evidence": evidence,
        "last_run_id": run_id,
    }


def import_flows_into_items(
    flows: list[dict[str, Any]],
    *,
    run_id: str,
    existing_items: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Merge flow rows into backlog items (by ref F-xx)."""
    existing = list(existing_items or [])
    by_ref = {str(i.get("ref")): i for i in existing if i.get("ref")}
    for flow in flows:
        ref = str(flow.get("id") or "")
        if not ref:
            continue
        new_item = flow_to_backlog_item(flow, run_id=run_id)
        if ref in by_ref:
            old = by_ref[ref]
            new_item["id"] = old.get("id") or new_item["id"]
            if old.get("status") == "done":
                new_item["status"] = "done"
            if old.get("evidence"):
                new_item["evidence"] = list(
                    dict.fromkeys(list(old["evidence"]) + list(new_item.get("evidence") or []))
                )
        by_ref[ref] = new_item
    hygiene = [i for i in existing if i.get("category") == "hygiene"]
    hygiene_ids = {i.get("id") for i in hygiene}
    for h in default_hygiene_items():
        if h["id"] not in hygiene_ids:
            hygiene.append(dict(h))
    flow_items = sorted(
        by_ref.values(), key=lambda x: (_priority_int(x.get("priority")), x.get("id", ""))
    )
    return hygiene + flow_items


def create_backlog(
    app_name: str,
    *,
    slug: Optional[str] = None,
    framework: str = "unknown",
    flows: Optional[list[dict[str, Any]]] = None,
    run_id: Optional[str] = None,
) -> dict[str, Any]:
    slug = slug or slug_from_app_name(app_name)
    run_id = run_id or _new_run_id(slug)
    items: list[dict[str, Any]] = []
    if flows:
        items = import_flows_into_items(flows, run_id=run_id)
    else:
        items = [dict(i) for i in default_hygiene_items()]
    return {
        "version": BACKLOG_VERSION,
        "app_name": app_name,
        "app_slug": slug,
        "framework": framework,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "items": items,
        "progress": compute_progress(items),
        "next_item_id": (next_pending_item({"items": items}) or {}).get("id"),
    }


def add_discovered_items(
    backlog: dict[str, Any],
    candidates: list[dict[str, Any]],
    *,
    run_id: str,
) -> int:
    """Append new flow candidates (discover_flows). Dedupe by ref or title+parent."""
    items = backlog.setdefault("items", [])
    seen_refs = {str(i.get("ref")) for i in items if i.get("ref")}
    seen_keys = {
        (str(i.get("title")), str(i.get("parent_id")))
        for i in items
        if i.get("category") == "flow"
    }
    added = 0
    max_num = 0
    for i in items:
        m = re.match(r"^W-F-(\d+)$", str(i.get("id") or ""))
        if m:
            max_num = max(max_num, int(m.group(1)))
    for cand in candidates:
        ref = str(cand.get("ref") or cand.get("id") or "")
        title = str(cand.get("title") or "")
        parent_id = cand.get("parent_id")
        if ref and ref in seen_refs:
            continue
        key = (title, str(parent_id))
        if title and key in seen_keys:
            continue
        max_num += 1
        wid = f"W-F-{max_num:02d}" if not ref.startswith("F-") else f"W-{ref}"
        if ref.startswith("F-"):
            wid = f"W-{ref}"
        items.append(
            {
                "id": wid,
                "category": cand.get("category") or "flow",
                "status": "pending",
                "title": title or wid,
                "success_criteria": cand.get("success_criteria") or "",
                "notes": cand.get("notes") or "",
                "ref": ref if ref.startswith("F-") else f"F-{max_num:02d}",
                "source": "discovered",
                "priority": _priority_int(cand.get("priority")),
                "parent_id": parent_id,
                "kind": cand.get("kind"),
                "evidence": [],
                "last_run_id": run_id,
            }
        )
        if ref:
            seen_refs.add(ref)
        seen_keys.add(key)
        added += 1
    return added


def mark_item(
    backlog: dict[str, Any],
    item_id: str,
    status: str,
    *,
    notes: Optional[str] = None,
    evidence: Optional[str] = None,
    run_id: Optional[str] = None,
) -> bool:
    if status not in ITEM_STATUSES:
        raise ValueError(f"invalid status: {status}")
    for item in backlog.get("items") or []:
        if str(item.get("id")) != str(item_id):
            continue
        item["status"] = status
        if notes is not None:
            item["notes"] = notes
        if evidence:
            ev = list(item.get("evidence") or [])
            if evidence not in ev:
                ev.append(evidence)
            item["evidence"] = ev
        if run_id:
            item["last_run_id"] = run_id
        item["updated_at"] = _now_iso()
        return True
    return False


def render_backlog_markdown(backlog: dict[str, Any]) -> str:
    prog = backlog.get("progress") or compute_progress(backlog.get("items") or [])
    lines = [
        f"# Backlog lab — {backlog.get('app_name', '?')}",
        "",
        f"- **Slug:** `{backlog.get('app_slug', '')}`",
        f"- **Framework:** {backlog.get('framework', 'unknown')}",
        f"- **Actualizado:** {backlog.get('updated_at', '')}",
        f"- **Progreso:** done {prog.get('done', 0)} / total {prog.get('total', 0)} "
        f"| pending {prog.get('pending', 0)} | blocked {prog.get('blocked', 0)} "
        f"| **complete:** `{prog.get('complete')}`",
        f"- **Siguiente ítem:** `{backlog.get('next_item_id') or '—'}`",
        "",
        "> Generado por `scripts/render_app_backlog.py`. **No editar a mano.** "
        "Cambios solo vía `backlog.json` (API `app_backlog_lib` / agente tras cada turno).",
        "",
        "| ID | Cat | Status | Pri | Ref | Título | Notas |",
        "|----|-----|--------|-----|-----|--------|-------|",
    ]
    for item in backlog.get("items") or []:
        notes = (item.get("notes") or "").replace("|", "/").replace("\n", " ")[:80]
        title = (item.get("title") or "").replace("|", "/")[:60]
        lines.append(
            f"| {item.get('id', '')} | {item.get('category', '')} | "
            f"{item.get('status', '')} | {item.get('priority', '')} | "
            f"{item.get('ref', '')} | {title} | {notes} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_backlog_md(slug: str, backlog: dict[str, Any]) -> Path:
    path = backlog_md_path(slug)
    path.write_text(render_backlog_markdown(backlog) + "\n", encoding="utf-8")
    return path


def load_state() -> dict[str, Any]:
    if not STATE_PATH.is_file():
        return {}
    return json.loads(STATE_PATH.read_text(encoding="utf-8-sig"))


def patch_state_for_app(
    app_name: str,
    slug: str,
    run_id: str,
    backlog_path: Path,
) -> None:
    state = load_state()
    state["active_lab"] = app_name
    state["active_app_slug"] = slug
    state["active_run"] = run_id
    try:
        state["backlog_ref"] = str(backlog_path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        state["backlog_ref"] = str(backlog_path).replace("\\", "/")
    lab_apps = state.setdefault("lab_apps", {})
    entry = lab_apps.setdefault(app_name, {})
    entry["backlog_ref"] = state["backlog_ref"]
    entry["active_run"] = run_id
    entry["app_slug"] = slug
    manifest = load_manifest(slug)
    prog = load_backlog(slug)
    if prog:
        entry["backlog_progress"] = prog.get("progress")
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8-sig")


def init_or_resume(
    app_name: str,
    *,
    import_flows_path: Optional[Path] = None,
    run_id: Optional[str] = None,
    framework: str = "unknown",
) -> dict[str, Any]:
    """Create backlog if missing; else load. Updates manifest + state.json pointers."""
    slug = slug_from_app_name(app_name)
    existing = load_backlog(slug)
    created = False
    manifest = load_manifest(slug)

    if existing is None:
        flows: list[dict[str, Any]] = []
        if import_flows_path and import_flows_path.is_file():
            data = json.loads(import_flows_path.read_text(encoding="utf-8-sig"))
            flows = data.get("flows") or []
            framework = data.get("framework") or framework
        run_id = run_id or _new_run_id(slug)
        existing = create_backlog(
            app_name,
            slug=slug,
            framework=framework,
            flows=flows or None,
            run_id=run_id,
        )
        created = True
    else:
        st = load_state()
        run_id = (
            run_id
            or manifest.get("active_run")
            or st.get("active_run")
            or _new_run_id(slug)
        )

    save_backlog(slug, existing)
    write_backlog_md(slug, existing)
    manifest.update(
        {
            "app_name": app_name,
            "app_slug": slug,
            "active_run": run_id,
            "framework": existing.get("framework") or framework,
        }
    )
    save_manifest(slug, manifest)
    run_dir = RUNS_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    patch_state_for_app(app_name, slug, run_id, backlog_json_path(slug))
    nxt = next_pending_item(existing)
    return {
        "created": created,
        "resumed": not created,
        "app_name": app_name,
        "app_slug": slug,
        "run_id": run_id,
        "backlog_path": str(backlog_json_path(slug)),
        "progress": existing.get("progress"),
        "next_item": nxt,
    }


def backlog_hint_for_state(state: dict[str, Any]) -> str:
    """Short next-step line for check_mcp_objective hook."""
    slug = state.get("active_app_slug")
    if not slug and state.get("active_lab"):
        slug = slug_from_app_name(str(state["active_lab"]))
    if not slug:
        return ""
    backlog = load_backlog(slug)
    if not backlog:
        return (
            f"backlog: NO EXISTE para slug '{slug}' -> "
            f"python scripts/init_or_resume_app_backlog.py \"{state.get('active_lab')}\""
        )
    prog = backlog.get("progress") or {}
    if prog.get("complete"):
        return (
            "backlog app COMPLETE (sin pending/blocked); "
            "opcional discover_flows por valor MCP o evaluacion honesta + perfect gate"
        )
    nxt = next_pending_item(backlog)
    if not nxt:
        return "backlog: sin ítem ejecutable (revisar parent_id / blocked)"
    title = (nxt.get("title") or "")[:55]
    return (
        f"backlog CANONICO: ejecutar {nxt.get('id')} "
        f"({nxt.get('category')}) {title} — un paso OBS->ACT->VERIFY; "
        f"luego mark_item done + render_app_backlog"
    )

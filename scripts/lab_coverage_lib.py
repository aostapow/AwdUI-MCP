"""Lab coverage: MCP capability catalog, usage aggregation, improvement tracking."""
from __future__ import annotations

import ast
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "mcp-servers" / "awdui-server" / "tools"
UIA_MAP = REPO_ROOT / "mcp-servers" / "awdui-server" / "detection" / "data" / "uia_control_map.json"
CATALOG_PATH = REPO_ROOT / "lab-apps" / "mcp-capability-catalog.json"


def _discover_mcp_tools() -> dict[str, dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    for path in sorted(TOOLS_DIR.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            is_tool = any(
                (isinstance(d, ast.Call) and getattr(d.func, "attr", "") == "tool")
                or (isinstance(d, ast.Attribute) and d.attr == "tool")
                for d in node.decorator_list
            )
            if not is_tool:
                continue
            doc = ast.get_docstring(node) or ""
            first = doc.strip().split("\n")[0] if doc.strip() else ""
            found[node.name] = {"module": path.stem, "summary": first}
    return found


def _load_uia_map() -> dict[str, Any]:
    return json.loads(UIA_MAP.read_text(encoding="utf-8-sig"))


def build_capability_catalog() -> dict[str, Any]:
    tools = _discover_mcp_tools()
    uia = _load_uia_map()
    controls: dict[str, Any] = {}
    all_act_tools: set[str] = set()
    all_act_methods: set[str] = set()
    all_patterns: set[str] = set()
    all_read_tools: set[str] = set()

    for name, spec in (uia.get("controls") or {}).items():
        patterns_ms = spec.get("patterns_ms") or {}
        for bucket in ("must", "conditional", "not"):
            for p in patterns_ms.get(bucket) or []:
                all_patterns.add(str(p))
        read_tools = list(spec.get("read") or [])
        all_read_tools.update(read_tools)
        acts: list[dict[str, Any]] = []
        for act in spec.get("act") or []:
            act_id = act.get("id") or ""
            act_tools = list(act.get("tools") or [])
            act_patterns = list(act.get("patterns") or [])
            all_act_methods.add(act_id)
            all_act_tools.update(act_tools)
            all_patterns.update(act_patterns)
            acts.append(
                {
                    "id": act_id,
                    "tools": act_tools,
                    "patterns": act_patterns,
                    "steps": act.get("steps") or [],
                }
            )
        controls[name] = {
            "read_tools": read_tools,
            "fallback": list(spec.get("fallback") or []),
            "patterns_ms": patterns_ms,
            "act_methods": acts,
        }

    act_bindings = []
    for ctrl, spec in controls.items():
        for act in spec["act_methods"]:
            for tool in act["tools"]:
                act_bindings.append(
                    {
                        "control": ctrl,
                        "act_method": act["id"],
                        "tool": tool,
                        "patterns": act["patterns"],
                    }
                )

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mcp_tools": {
            "total": len(tools),
            "tools": {k: v for k, v in sorted(tools.items())},
        },
        "uia_controls": {
            "total": len(controls),
            "controls": controls,
        },
        "uia_patterns_ms": sorted(all_patterns),
        "act_methods": {
            "total": len(all_act_methods),
            "ids": sorted(all_act_methods),
        },
        "act_bindings": {
            "total": len(act_bindings),
            "items": act_bindings,
        },
        "read_tools_catalog": sorted(all_read_tools | all_act_tools),
        "frameworks_known": ["uwp", "win32", "winforms", "wpf", "electron", "java_swing", "gtk", "unknown"],
    }


def write_catalog(path: Path | None = None) -> dict[str, Any]:
    path = path or CATALOG_PATH
    catalog = build_capability_catalog()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    return catalog


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _pct(used: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(100.0 * used / total, 1)


def aggregate_usage(
    catalog: dict[str, Any],
    usage_rows: list[dict[str, Any]],
    *,
    framework: str = "unknown",
) -> dict[str, Any]:
    tool_counts: dict[str, int] = {}
    tool_outcomes: dict[str, dict[str, int]] = {}
    roles_seen: set[str] = set()
    roles_interacted: set[str] = set()
    patterns_used: set[str] = set()
    act_methods_used: set[str] = set()
    bindings_used: set[tuple[str, str, str]] = set()

    for row in usage_rows:
        tool = row.get("tool") or row.get("mcp_tool")
        if tool:
            tool_counts[str(tool)] = tool_counts.get(str(tool), 0) + 1
            outcome = str(row.get("outcome") or "unknown")
            tool_outcomes.setdefault(str(tool), {})
            tool_outcomes[str(tool)][outcome] = tool_outcomes[str(tool)].get(outcome, 0) + 1
        role = row.get("uia_role") or row.get("role")
        if role:
            roles_seen.add(str(role))
            if row.get("interacted"):
                roles_interacted.add(str(role))
            if tool and row.get("interacted"):
                roles_interacted.add(str(role))
        if row.get("interacted") and role:
            roles_interacted.add(str(role))
        pat = row.get("uia_pattern") or row.get("pattern")
        if pat:
            patterns_used.add(str(pat))
        am = row.get("act_method")
        if am:
            act_methods_used.add(str(am))
        ctrl = row.get("uia_control") or row.get("control")
        if ctrl and am and tool:
            bindings_used.add((str(ctrl), str(am), str(tool)))

    all_tools = sorted((catalog.get("mcp_tools") or {}).get("tools", {}).keys())
    used_tools = sorted(tool_counts.keys())
    unused_tools = sorted(set(all_tools) - set(used_tools))

    all_controls = sorted((catalog.get("uia_controls") or {}).get("controls", {}).keys())
    unused_controls = sorted(set(all_controls) - roles_seen)
    seen_not_interacted = sorted(roles_seen - roles_interacted)

    all_act_ids = set((catalog.get("act_methods") or {}).get("ids") or [])
    unused_act_methods = sorted(all_act_ids - act_methods_used)

    all_patterns = set(catalog.get("uia_patterns_ms") or [])
    unused_patterns = sorted(all_patterns - patterns_used)

    binding_items = (catalog.get("act_bindings") or {}).get("items") or []
    all_binding_keys = {
        (b["control"], b["act_method"], b["tool"]) for b in binding_items
    }
    unused_bindings = sorted(all_binding_keys - bindings_used)

    return {
        "framework": framework,
        "mcp_tools": {
            "universe_total": len(all_tools),
            "used_total": len(used_tools),
            "coverage_pct": _pct(len(used_tools), len(all_tools)),
            "used": used_tools,
            "unused": unused_tools,
            "counts": tool_counts,
            "outcomes_by_tool": tool_outcomes,
        },
        "uia_controls": {
            "universe_total": len(all_controls),
            "seen_in_lab_total": len(roles_seen),
            "interacted_total": len(roles_interacted),
            "seen_coverage_pct": _pct(len(roles_seen), len(all_controls)),
            "interaction_coverage_pct": _pct(len(roles_interacted), len(roles_seen))
            if roles_seen
            else 0.0,
            "seen": sorted(roles_seen),
            "interacted": sorted(roles_interacted),
            "seen_not_interacted": seen_not_interacted,
            "never_seen": unused_controls,
        },
        "uia_patterns": {
            "universe_total": len(all_patterns),
            "used_total": len(patterns_used),
            "coverage_pct": _pct(len(patterns_used), len(all_patterns)),
            "used": sorted(patterns_used),
            "unused": unused_patterns,
        },
        "act_methods": {
            "universe_total": len(all_act_ids),
            "used_total": len(act_methods_used),
            "coverage_pct": _pct(len(act_methods_used), len(all_act_ids)),
            "used": sorted(act_methods_used),
            "unused": unused_act_methods,
        },
        "act_bindings": {
            "universe_total": len(all_binding_keys),
            "used_total": len(bindings_used),
            "coverage_pct": _pct(len(bindings_used), len(all_binding_keys)),
            "unused_sample": [
                {"control": c, "act_method": m, "tool": t}
                for c, m, t in unused_bindings[:30]
            ],
            "unused_total": len(unused_bindings),
        },
        "invocation_count": len(usage_rows),
    }


def aggregate_improvements(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_kind: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        kind = str(row.get("kind") or "other")
        by_kind.setdefault(kind, []).append(row)
    return {
        "total": len(rows),
        "by_kind": {k: len(v) for k, v in sorted(by_kind.items())},
        "items": rows,
    }


def _load_yaml_simple(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data: dict[str, Any] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        m = re.match(r"^(\w+):\s*(.+)$", line.strip())
        if m:
            data[m.group(1)] = m.group(2).strip()
    return data


def summarize_flows(flows_path: Path) -> dict[str, Any]:
    if not flows_path.is_file():
        return {}
    try:
        data = json.loads(flows_path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}
    flows = data.get("flows") or []
    by_status: dict[str, int] = {}
    for f in flows:
        st = str(f.get("status") or "unknown")
        by_status[st] = by_status.get(st, 0) + 1
    return {
        "total": len(flows),
        "by_status": by_status,
        "by_kind": {
            "entry": sum(1 for f in flows if f.get("kind") == "entry"),
            "action": sum(1 for f in flows if f.get("kind") == "action"),
        },
        "by_source": {
            "seed": sum(1 for f in flows if f.get("source") in ("seed", "user")),
            "discovered": sum(1 for f in flows if f.get("source") == "discovered"),
        },
    }


def build_lab_report(run_dir: Path, catalog_path: Path | None = None) -> dict[str, Any]:
    catalog_path = catalog_path or CATALOG_PATH
    if not catalog_path.is_file():
        catalog = write_catalog(catalog_path)
    else:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8-sig"))

    usage_rows = load_jsonl(run_dir / "mcp-usage.jsonl")
    # Also merge tool hits from evidence.jsonl when present
    for row in load_jsonl(run_dir / "evidence.jsonl"):
        if row.get("tool") or row.get("mcp_tool"):
            usage_rows.append(row)

    discovered = _load_yaml_simple(run_dir / "discovered.yaml")
    framework = str(discovered.get("framework") or "unknown")

    improvements = aggregate_improvements(load_jsonl(run_dir / "improvements.jsonl"))
    usage = aggregate_usage(catalog, usage_rows, framework=framework)
    flows = summarize_flows(run_dir / "flows.json")

    try:
        catalog_ref = str(catalog_path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        catalog_ref = str(catalog_path)

    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_dir.name,
        "app_name": discovered.get("app_name"),
        "framework": framework,
        "catalog_ref": catalog_ref,
        "catalog_generated_at": catalog.get("generated_at"),
        "usage": usage,
        "flows": flows,
        "improvements": improvements,
    }
    return report


def format_markdown_report(report: dict[str, Any]) -> str:
    u = report.get("usage") or {}
    mt = u.get("mcp_tools") or {}
    uc = u.get("uia_controls") or {}
    imp = report.get("improvements") or {}
    flows = report.get("flows") or {}

    lines = [
        f"# Informe lab — {report.get('app_name') or report.get('run_id')}",
        "",
        f"- **Run:** `{report.get('run_id')}`",
        f"- **Framework:** {report.get('framework')}",
        f"- **Generado:** {report.get('generated_at')}",
        "",
        "## Cobertura MCP (tools)",
        "",
        f"- Universo: **{mt.get('universe_total', 0)}** tools registradas",
        f"- Usadas en este lab: **{mt.get('used_total', 0)}** ({mt.get('coverage_pct', 0)}%)",
        f"- Invocaciones registradas: **{u.get('invocation_count', 0)}**",
        "",
    ]
    if mt.get("used"):
        lines.append("### Tools usadas")
        for t in mt["used"]:
            cnt = (mt.get("counts") or {}).get(t, 0)
            lines.append(f"- `{t}` × {cnt}")
        lines.append("")

    unused = mt.get("unused") or []
    if unused:
        lines.append(f"### Tools sin uso en este lab ({len(unused)})")
        for t in unused[:25]:
            lines.append(f"- `{t}`")
        if len(unused) > 25:
            lines.append(f"- … y {len(unused) - 25} más (ver `coverage.json`)")
        lines.append("")

    lines.extend(
        [
            "## Cobertura UIA (controles y métodos)",
            "",
            f"- Controles en catálogo MS/MCP: **{uc.get('universe_total', 0)}**",
            f"- Controles **vistos** en la app: **{uc.get('seen_in_lab_total', 0)}** "
            f"({uc.get('seen_coverage_pct', 0)}% del catálogo)",
            f"- Controles **con interacción**: **{uc.get('interacted_total', 0)}** "
            f"({uc.get('interaction_coverage_pct', 0)}% de los vistos)",
            "",
        ]
    )
    sni = uc.get("seen_not_interacted") or []
    if sni:
        lines.append("### Vistos pero no interactuados")
        for r in sni[:20]:
            lines.append(f"- `{r}`")
        lines.append("")

    am = u.get("act_methods") or {}
    lines.extend(
        [
            f"- Métodos de actuación (map_*): **{am.get('used_total', 0)}** / "
            f"{am.get('universe_total', 0)} ({am.get('coverage_pct', 0)}%)",
            "",
        ]
    )

    if flows:
        lines.extend(
            [
                "## Flujos funcionales",
                "",
                f"- Total en catálogo: **{flows.get('total', 0)}**",
                f"- Por estado: `{flows.get('by_status')}`",
                f"- Entry / action: `{flows.get('by_kind')}`",
                f"- Seed / discovered: `{flows.get('by_source')}`",
                "",
            ]
        )

    lines.extend(
        [
            "## Mejoras MCP durante la corrida",
            "",
            f"- Registros: **{imp.get('total', 0)}**",
            f"- Por tipo: `{imp.get('by_kind')}`",
            "",
        ]
    )
    for item in (imp.get("items") or [])[-15:]:
        kind = item.get("kind", "?")
        summary = item.get("summary", "")
        benefit = item.get("benefit", "")
        lines.append(f"- **[{kind}]** {summary}")
        if benefit:
            lines.append(f"  - Beneficio: {benefit}")
    lines.append("")
    lines.append("Detalle completo: `coverage.json`, `improvements.jsonl`, `mcp-usage.jsonl`.")
    return "\n".join(lines)


def write_lab_report(run_dir: Path, catalog_path: Path | None = None) -> tuple[Path, Path]:
    report = build_lab_report(run_dir, catalog_path)
    json_path = run_dir / "coverage.json"
    md_path = run_dir / "lab-summary.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(format_markdown_report(report), encoding="utf-8")
    return json_path, md_path


def coverage_summary_line(report: dict[str, Any]) -> str:
    usage = report.get("usage") or {}
    mt = usage.get("mcp_tools") or {}
    uc = usage.get("uia_controls") or {}
    imp = report.get("improvements") or {}
    flows = report.get("flows") or {}
    return (
        f"tools {mt.get('used_total', 0)}/{mt.get('universe_total', 0)} "
        f"({mt.get('coverage_pct', 0)}%) "
        f"uia_visto {uc.get('seen_in_lab_total', 0)}/{uc.get('universe_total', 0)} "
        f"flujos {flows.get('total', 0)} mejoras {imp.get('total', 0)}"
    )


def compute_flows_progress(flows_data: dict[str, Any]) -> dict[str, Any]:
    """Summarize flows.json for lab_apps.{app}.flows_progress."""
    flows = flows_data.get("flows") or []
    by_status: dict[str, int] = {}
    entry_n = action_n = 0
    for flow in flows:
        if not isinstance(flow, dict):
            continue
        kind = flow.get("kind")
        if kind == "entry":
            entry_n += 1
        elif kind == "action":
            action_n += 1
        status = str(flow.get("status") or "pending")
        by_status[status] = by_status.get(status, 0) + 1
    cycle = flows_data.get("cycle") or {}
    return {
        "total": len(flows),
        "entry_total": entry_n,
        "action_total": action_n,
        "met": by_status.get("met", 0),
        "pending": by_status.get("pending", 0),
        "exploring": by_status.get("exploring", 0),
        "partial": by_status.get("partial", 0),
        "blocked": by_status.get("blocked", 0),
        "cancelled": by_status.get("cancelled", 0),
        "last_mode": cycle.get("last_mode"),
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def sync_state_coverage(
    state_path: Path,
    active_lab: str,
    active_run: str,
    report: dict[str, Any],
    *,
    run_dir: Path | None = None,
) -> None:
    """Patch lab_apps.{active_lab}.coverage and flows_progress in state.json."""
    if not state_path.is_file():
        return
    try:
        data = json.loads(state_path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return

    usage = report.get("usage") or {}
    mt = usage.get("mcp_tools") or {}
    uc = usage.get("uia_controls") or {}
    am = usage.get("act_methods") or {}
    imp = report.get("improvements") or {}

    coverage = {
        "last_report": f"runs/{active_run}/coverage.json",
        "lab_summary": f"runs/{active_run}/lab-summary.md",
        "mcp_tools_pct": mt.get("coverage_pct"),
        "mcp_tools_used": mt.get("used_total"),
        "mcp_tools_universe": mt.get("universe_total"),
        "uia_controls_seen_pct": uc.get("seen_coverage_pct"),
        "uia_controls_interacted": uc.get("interacted_total"),
        "act_methods_pct": am.get("coverage_pct"),
        "improvements_total": imp.get("total"),
        "invocation_count": usage.get("invocation_count"),
        "updated_at": report.get("generated_at"),
    }

    flows_progress: dict[str, Any] | None = None
    flows_path = (run_dir / "flows.json") if run_dir else None
    if flows_path and flows_path.is_file():
        try:
            flows_data = json.loads(flows_path.read_text(encoding="utf-8-sig"))
            flows_progress = compute_flows_progress(flows_data)
        except (json.JSONDecodeError, OSError):
            pass

    lab_apps = data.setdefault("lab_apps", {})
    entry = lab_apps.setdefault(str(active_lab), {})
    entry["coverage"] = coverage
    if flows_progress is not None:
        entry["flows_progress"] = flows_progress

    state_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8",
    )

    if run_dir and run_dir.is_dir():
        sidecar = {
            "active_lab": str(active_lab),
            "active_run": str(active_run),
            "coverage": coverage,
            "flows_progress": flows_progress,
            "generated_at": report.get("generated_at"),
        }
        try:
            (run_dir / "coverage-sync.json").write_text(
                json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass


def incremental_lab_coverage(
    run_dir: Path,
    *,
    state_path: Path | None = None,
    active_lab: str | None = None,
    active_run: str | None = None,
    catalog_path: Path | None = None,
) -> dict[str, Any]:
    """Regenerate coverage.json + lab-summary.md; optionally sync state.json."""
    write_lab_report(run_dir, catalog_path)
    report = build_lab_report(run_dir, catalog_path)
    run_id = active_run or run_dir.name
    if state_path and active_lab:
        sync_state_coverage(
            state_path,
            active_lab,
            run_id,
            report,
            run_dir=run_dir,
        )
    try:
        write_coverage_diff(run_dir)
    except Exception:
        pass
    try:
        scripts_dir = Path(__file__).resolve().parent
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        from repo_snapshot_lib import write_repo_snapshot

        write_repo_snapshot(run_dir)
    except Exception:
        pass
    return {
        "summary_line": coverage_summary_line(report),
        "report": report,
    }


def _load_coverage_report(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None


def find_previous_run_coverage(
    run_dir: Path,
    runs_root: Path | None = None,
) -> Path | None:
    """Latest sibling run with coverage.json and same app_name (if known)."""
    runs_root = runs_root or run_dir.parent
    current = _load_coverage_report(run_dir / "coverage.json")
    app_name = (current or {}).get("app_name")
    candidates: list[tuple[float, Path]] = []
    for sibling in runs_root.iterdir():
        if not sibling.is_dir() or sibling.resolve() == run_dir.resolve():
            continue
        cov = sibling / "coverage.json"
        if not cov.is_file():
            continue
        prev = _load_coverage_report(cov)
        if app_name and prev and prev.get("app_name") != app_name:
            continue
        candidates.append((cov.stat().st_mtime, cov))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def build_coverage_diff(
    current_report: dict[str, Any],
    previous_report: dict[str, Any],
) -> dict[str, Any]:
    cur_u = (current_report.get("usage") or {}).get("mcp_tools") or {}
    prev_u = (previous_report.get("usage") or {}).get("mcp_tools") or {}
    cur_used = set(cur_u.get("used") or [])
    prev_used = set(prev_u.get("used") or [])
    cur_imp = current_report.get("improvements") or {}
    prev_imp = previous_report.get("improvements") or {}
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "current_run": current_report.get("run_id"),
        "previous_run": previous_report.get("run_id"),
        "app_name": current_report.get("app_name"),
        "mcp_tools": {
            "current_pct": cur_u.get("coverage_pct"),
            "previous_pct": prev_u.get("coverage_pct"),
            "delta_pct": round(
                float(cur_u.get("coverage_pct") or 0)
                - float(prev_u.get("coverage_pct") or 0),
                1,
            ),
            "newly_used": sorted(cur_used - prev_used),
            "no_longer_used": sorted(prev_used - cur_used),
        },
        "improvements_delta": int(cur_imp.get("total") or 0)
        - int(prev_imp.get("total") or 0),
    }


def format_coverage_diff_md(diff: dict[str, Any]) -> str:
    mt = diff.get("mcp_tools") or {}
    lines = [
        "# Diff de cobertura lab",
        "",
        f"- **App:** {diff.get('app_name')}",
        f"- **Corrida actual:** `{diff.get('current_run')}`",
        f"- **Corrida anterior:** `{diff.get('previous_run')}`",
        f"- **Tools:** {mt.get('previous_pct')}% → {mt.get('current_pct')}% "
        f"(Δ {mt.get('delta_pct')}%)",
        f"- **Mejoras nuevas:** {diff.get('improvements_delta')}",
        "",
    ]
    if mt.get("newly_used"):
        lines.append("## Tools nuevas en esta corrida")
        for t in mt["newly_used"]:
            lines.append(f"- `{t}`")
        lines.append("")
    return "\n".join(lines)


def write_coverage_diff(run_dir: Path) -> Path | None:
    prev_path = find_previous_run_coverage(run_dir)
    current = build_lab_report(run_dir)
    if not prev_path:
        return None
    previous = json.loads(prev_path.read_text(encoding="utf-8-sig"))
    diff = build_coverage_diff(current, previous)
    out = run_dir / "coverage-diff.json"
    out.write_text(json.dumps(diff, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "coverage-diff.md").write_text(format_coverage_diff_md(diff), encoding="utf-8")
    return out

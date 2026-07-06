"""Match live locator queries to stored repository objects."""
from __future__ import annotations

import re
from typing import Optional

from detection.app_identity import title_app_name
from detection.object_repository import list_objects


def _norm(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def _window_key_for_title(window_title: Optional[str]) -> Optional[str]:
    token = title_app_name(window_title)
    if not token:
        return None
    return re.sub(r"[^\w\-]", "_", token)[:48] or None


def _window_matches(window_key: str, window_title: Optional[str]) -> bool:
    if not window_title:
        return True
    wk = _norm(window_key).replace("_", " ")
    wt = _norm(window_title).replace("_", " ")
    return wt in wk or wk in wt or wk == wt


def _ident_name(obj: dict) -> str:
    ident = obj.get("identification") or {}
    for tier in ("mandatory", "assistive", "smart"):
        for key in ("name", "text"):
            val = ident.get(tier, {}).get(key)
            if val:
                return str(val)
    fp = obj.get("full_properties") or {}
    return str(fp.get("name") or obj.get("logical_name") or "")


def score_repo_object(
    obj: dict,
    *,
    name: Optional[str] = None,
    role: Optional[str] = None,
    automation_id: Optional[str] = None,
    window_title: Optional[str] = None,
) -> int:
    """Higher is better; 0 means no match."""
    repo_path = obj.get("repo_path") or ""
    if not repo_path:
        return 0

    parts = [p for p in repo_path.split("/") if p]
    window_key = parts[0] if parts else ""
    leaf = parts[-1] if parts else ""

    if not _window_matches(window_key, window_title):
        return 0

    score = 0
    ident = obj.get("identification") or {}
    obj_auto = (
        obj.get("automation_id")
        or ident.get("mandatory", {}).get("automation_id")
        or ""
    )
    logical = _norm(obj.get("logical_name"))
    leaf_norm = _norm(leaf)
    name_norm = _norm(name)
    auto_norm = _norm(automation_id)
    role_norm = _norm(role).replace("controltype.", "") if role else ""

    if auto_norm:
        if auto_norm == _norm(obj_auto):
            score += 1000
        if auto_norm == leaf_norm:
            score += 950
        if auto_norm in leaf_norm:
            score += 700

    if name_norm:
        if name_norm == logical:
            score += 900
        if name_norm == leaf_norm:
            score += 880
        if name_norm.isdigit():
            if leaf_norm == f"num{name_norm}button":
                score += 920
            elif f"num{name_norm}" in leaf_norm:
                score += 800
        ident_name = _norm(_ident_name(obj))
        if name_norm and name_norm == ident_name:
            score += 850
        if name_norm in leaf_norm:
            score += 450
        if name_norm in _norm(repo_path):
            score += 200

    if role_norm:
        assist_role = _norm(ident.get("assistive", {}).get("role", ""))
        swf = _norm(obj.get("class", ""))
        if role_norm == assist_role or role_norm in swf:
            score += 120

    lr = obj.get("last_resolution") or {}
    score += min(int(lr.get("success_count") or 0), 40)

    return score


def _collect_objects(
    repo: dict,
    window_title: Optional[str],
    *,
    name: Optional[str] = None,
    automation_id: Optional[str] = None,
) -> list[dict]:
    objects: list[dict] = []
    seen: set[str] = set()

    preferred_key = _window_key_for_title(window_title)
    if preferred_key:
        for obj in list_objects(repo, preferred_key):
            path = obj.get("repo_path")
            if path and path not in seen:
                seen.add(path)
                objects.append(obj)

    for obj in list_objects(repo, None):
        path = obj.get("repo_path")
        if path and path not in seen:
            seen.add(path)
            objects.append(obj)

    return objects


def find_best_repo_path(
    repo: dict,
    *,
    name: Optional[str] = None,
    role: Optional[str] = None,
    automation_id: Optional[str] = None,
    window_title: Optional[str] = None,
    min_score: int = 400,
) -> Optional[str]:
    """Return the best matching repo_path for a locator query, if any."""
    if not any((name, role, automation_id)):
        return None

    ranked: list[tuple[int, str]] = []
    for obj in _collect_objects(repo, window_title, name=name, automation_id=automation_id):
        score = score_repo_object(
            obj,
            name=name,
            role=role,
            automation_id=automation_id,
            window_title=window_title,
        )
        if score > 0:
            ranked.append((score, obj["repo_path"]))

    if not ranked:
        return None

    ranked.sort(key=lambda item: item[0], reverse=True)
    best_score, best_path = ranked[0]
    if best_score < min_score:
        return None
    if len(ranked) > 1 and ranked[1][0] == best_score:
        return None
    return best_path


def resolve_via_repository(
    orch,
    *,
    name: Optional[str] = None,
    role: Optional[str] = None,
    automation_id: Optional[str] = None,
    window_title: Optional[str] = None,
    repo_path: Optional[str] = None,
    index: int = 0,
) -> Optional[dict]:
    """Try repository resolution; return find_element-shaped dict or None."""
    try:
        from tools.framework_detect import do_detect_framework
        from detection.app_identity import repository_app_name
        from detection.object_repository import load_repo
        from detection.repo_resolver import resolve_repo_object
        from detection.element_coords import to_screen_coords

        fw = do_detect_framework(window_title)
        app_name, exe_path = repository_app_name(fw, window_title)
        repo = load_repo(app_name, exe_path)
        repo["exe_path"] = exe_path
        repo["framework"] = fw.get("framework", "unknown")

        path = repo_path or find_best_repo_path(
            repo,
            name=name,
            role=role,
            automation_id=automation_id,
            window_title=window_title,
        )
        if not path:
            return None

        result = resolve_repo_object(
            repo,
            path,
            orch,
            window_title=window_title,
        )
        if not result.get("found"):
            return None

        elem = result["element"]
        elements = [to_screen_coords(dict(elem), window_title)]
        if index > 0 and index >= len(elements):
            return None

        return {
            "found": True,
            "elements": elements,
            "backend_used": elem.get("backend_used", "repository"),
            "method": result.get("method", "repository"),
            "layer": "repository",
            "repo_path": path,
        }
    except Exception:
        return None

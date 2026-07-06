"""UFT-style object repository with image snapshots and hierarchical paths."""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Optional

from detection.winforms_map import build_identification, infer_swf_class

_REPO_DIR = Path.home() / ".awdui-mcp" / "repositories"


def _app_id(app_name: str, exe_path: str = "") -> str:
  raw = exe_path or app_name
  return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _repo_path(app_id: str) -> Path:
  return _REPO_DIR / f"{app_id}.json"


def _assets_dir(app_id: str) -> Path:
  d = _REPO_DIR / app_id / "assets"
  d.mkdir(parents=True, exist_ok=True)
  return d


def parse_repo_path(repo_path: str) -> tuple[str, list[str]]:
  """Parse 'windowKey/obj' or 'windowKey/parent/child/leaf' into window + object chain."""
  parts = [p for p in repo_path.strip("/").split("/") if p]
  if len(parts) < 2:
    raise ValueError("repo_path must be 'windowKey/objectName' or 'windowKey/parent/.../leaf'")
  return parts[0], parts[1:]


def load_repo(app_name: str, exe_path: str = "") -> dict:
  aid = _app_id(app_name, exe_path)
  path = _repo_path(aid)
  if path.exists():
    try:
      return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
      pass
  return {
    "app_id": aid,
    "app_name": app_name,
    "framework": "unknown",
    "windows": {},
  }


def save_repo(repo: dict) -> None:
  _REPO_DIR.mkdir(parents=True, exist_ok=True)
  path = _repo_path(repo["app_id"])
  path.write_text(json.dumps(repo, indent=2), encoding="utf-8")


def _ensure_window(repo: dict, window_key: str, title_pattern: str = "") -> dict:
  windows = repo.setdefault("windows", {})
  if window_key not in windows:
    windows[window_key] = {
      "title_pattern": title_pattern or f".*{re.escape(window_key)}.*",
      "objects": {},
    }
  return windows[window_key]


def _build_full_path(objects: dict, name: str, window_key: str) -> str:
  chain: list[str] = []
  current: str = name
  seen: set[str] = set()
  while current and current not in seen:
    seen.add(current)
    chain.insert(0, current)
    current = objects.get(current, {}).get("parent", "") or ""
  return f"{window_key}/{'/'.join(chain)}"


def get_object(repo: dict, repo_path: str) -> Optional[dict]:
  """repo_path: 'windowKey/objectName' or nested 'windowKey/parent/leaf'."""
  try:
    window_key, chain = parse_repo_path(repo_path)
  except ValueError:
    return None
  win = repo.get("windows", {}).get(window_key)
  if not win:
    return None
  objects = win.get("objects", {})
  leaf_name = chain[-1]
  obj = objects.get(leaf_name)
  if not obj:
    return None
  if len(chain) > 1:
    expected_parent = chain[-2]
    stored_parent = obj.get("parent", "")
    if stored_parent and stored_parent != expected_parent:
      return None
  out = dict(obj)
  out["repo_path"] = repo_path
  out["_window_key"] = window_key
  out["_object_name"] = chain[-1]
  return out


def upsert_object(
  repo: dict,
  repo_path: str,
  *,
  obj_class: str = "control",
  identification: dict | None = None,
  last_resolution: dict | None = None,
  snapshots: dict | None = None,
  parent: str = "",
  element: dict | None = None,
) -> dict:
  window_key, chain = parse_repo_path(repo_path)
  obj_name = chain[-1]
  if not parent and len(chain) > 1:
    parent = chain[-2]
  window = _ensure_window(repo, window_key)
  objects = window.setdefault("objects", {})

  for i, pname in enumerate(chain[:-1]):
    if pname not in objects:
      pparent = chain[i - 1] if i > 0 else ""
      objects[pname] = {
        "class": "SwfPage" if i > 0 else "SwfTab",
        "parent": pparent,
        "identification": {"mandatory": {"name": pname}, "assistive": {"role": "TabItem" if i > 0 else "Tab"}},
      }

  if element and obj_class == "control":
    obj_class = infer_swf_class(
      element.get("role", ""),
      element.get("class_name", ""),
      obj_class,
    )
  if element and not identification:
    identification = build_identification(element, obj_class)

  obj = objects.setdefault(obj_name, {"class": obj_class, "parent": parent})
  if parent:
    obj["parent"] = parent
  if obj_class and obj_class != "control":
    obj["class"] = obj_class
  if identification:
    obj["identification"] = identification
  if last_resolution:
    lr = obj.setdefault("last_resolution", {})
    lr.update(last_resolution)
    lr["success_count"] = lr.get("success_count", 0) + 1
    lr["last_success"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
  if snapshots:
    obj["snapshots"] = snapshots
  save_repo(repo)
  return obj


def list_objects(repo: dict, window_key: str | None = None) -> list[dict]:
  result = []
  windows = repo.get("windows", {})
  targets = {window_key: windows[window_key]} if window_key and window_key in windows else windows
  for wk, wdata in targets.items():
    objects = wdata.get("objects", {})
    for name in objects:
      full = _build_full_path(objects, name, wk)
      obj = dict(objects[name])
      result.append({"repo_path": full, **obj})
  return result


def assets_path(app_id: str, filename: str) -> Path:
  return _assets_dir(app_id) / filename


def relative_asset(app_id: str, filename: str) -> str:
  return f"{app_id}/assets/{filename}"

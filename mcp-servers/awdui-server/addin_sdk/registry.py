"""Discover, load, and lifecycle-manage AwdUI MCP addins."""
from __future__ import annotations

import importlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from addin_sdk.contract import AddinContext, AddinManifest, AwduiAddin

_REGISTRY: Optional["AddinRegistry"] = None


@dataclass
class LoadedAddin:
    manifest: AddinManifest
    instance: AwduiAddin
    root: Path
    ctx: AddinContext


@dataclass
class AddinRegistry:
    addins: list[LoadedAddin] = field(default_factory=list)
    tool_count: int = 0

    def loaded_ids(self) -> list[str]:
        return [a.manifest.id for a in self.addins]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_config() -> dict[str, Any]:
    from awdui_paths import addins_config_path, data_dir, user_addins_dir

    cfg_path = addins_config_path()
    if cfg_path.is_file():
        try:
            return json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    default = {
        "schema_version": 1,
        "addin_paths": [
            str(_repo_root() / "addins"),
            str(user_addins_dir()),
        ],
        "addins": {},
        "auto_activate": True,
    }
    data_dir().mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(default, indent=2), encoding="utf-8")
    return default


def _parse_manifest(path: Path) -> Optional[AddinManifest]:
    import json

    manifest_path = path
    if path.name == "manifest.yaml":
        json_alt = path.with_name("manifest.json")
        if json_alt.is_file():
            manifest_path = json_alt
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    addin_id = str(raw.get("id") or "").strip()
    if not addin_id:
        return None
    tools = raw.get("tools") or {}
    return AddinManifest(
        id=addin_id,
        name=str(raw.get("name") or addin_id),
        version=str(raw.get("version") or "0.0.0"),
        entry_module=str(raw.get("entry_module") or f"{addin_id}_addin"),
        enabled_by_default=bool(raw.get("enabled_by_default", False)),
        match=dict(raw.get("match") or {}),
        skills=[str(s) for s in (raw.get("skills") or [])],
        tool_namespace=str(tools.get("namespace") or f"{addin_id}_"),
    )


def discover_manifests(paths: list[Path]) -> list[Path]:
    found: list[Path] = []
    seen: set[str] = set()
    for base in paths:
        if not base.is_dir():
            continue
        for pattern in ("*/manifest.json", "*/manifest.yaml"):
            for manifest in sorted(base.glob(pattern)):
                addin_dir = manifest.parent.name
                if addin_dir in seen:
                    continue
                seen.add(addin_dir)
                found.append(manifest)
    return found


def _is_enabled(manifest: AddinManifest, config: dict[str, Any]) -> bool:
    addins_cfg = config.get("addins") or {}
    entry = addins_cfg.get(manifest.id)
    if isinstance(entry, dict) and "enabled" in entry:
        return bool(entry["enabled"])
    return manifest.enabled_by_default


def _load_entry(manifest_path: Path, manifest: AddinManifest) -> Optional[LoadedAddin]:
    root = manifest_path.parent
    entry = manifest.entry_module
    module_name = entry
    class_name = ""
    if ":" in entry:
        module_name, class_name = entry.split(":", 1)
    elif "." in entry and entry[0].isupper():
        parts = entry.rsplit(".", 1)
        module_name, class_name = parts[0], parts[1]

    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    try:
        mod = importlib.import_module(module_name)
    except Exception as exc:
        print(f"[AwdUI] addin {manifest.id}: failed to import {module_name}: {exc}", file=sys.stderr)
        return None

    if class_name:
        addin_cls = getattr(mod, class_name, None)
    else:
        addin_cls = None
        for attr in dir(mod):
            obj = getattr(mod, attr)
            if isinstance(obj, type) and issubclass(obj, AwduiAddin) and obj is not AwduiAddin:
                addin_cls = obj
                break
    if addin_cls is None:
        print(f"[AwdUI] addin {manifest.id}: no AwduiAddin class in {module_name}", file=sys.stderr)
        return None

    from awdui_paths import data_dir
    from tools.target_window import get_target

    ctx = AddinContext(
        data_dir=data_dir(),
        addin_root=root,
        manifest=manifest,
        log=lambda msg: print(f"[AwdUI addin:{manifest.id}] {msg}", file=sys.stderr),
        get_target_window=get_target,
    )
    try:
        instance = addin_cls()
        instance.manifest = manifest
        instance.on_load(ctx)
    except Exception as exc:
        print(f"[AwdUI] addin {manifest.id}: on_load failed: {exc}", file=sys.stderr)
        return None
    return LoadedAddin(manifest=manifest, instance=instance, root=root, ctx=ctx)


def bootstrap_addins(mcp: Any) -> AddinRegistry:
    """Load enabled addins and register their tools."""
    global _REGISTRY
    config = _default_config()
    paths = [Path(p) for p in config.get("addin_paths", [])]
    registry = AddinRegistry()
    for manifest_path in discover_manifests(paths):
        manifest = _parse_manifest(manifest_path)
        if manifest is None:
            continue
        if not _is_enabled(manifest, config):
            continue
        loaded = _load_entry(manifest_path, manifest)
        if loaded is None:
            continue
        try:
            count = loaded.instance.register_tools(mcp, loaded.ctx)
            registry.tool_count += int(count or 0)
            registry.addins.append(loaded)
            print(
                f"[AwdUI] addin loaded: {manifest.id} ({count} tools)",
                file=sys.stderr,
            )
        except Exception as exc:
            print(f"[AwdUI] addin {manifest.id}: register_tools failed: {exc}", file=sys.stderr)
    _REGISTRY = registry
    return registry


def get_registry() -> Optional[AddinRegistry]:
    return _REGISTRY


def shutdown_addins(registry: Optional[AddinRegistry] = None) -> None:
    global _REGISTRY
    reg = registry or _REGISTRY
    if not reg:
        return
    for loaded in reg.addins:
        try:
            loaded.instance.on_shutdown(loaded.ctx)
        except Exception:
            pass
    _REGISTRY = None

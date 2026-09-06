"""AwdUI Object Repository Studio — REST API."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional
from urllib.parse import unquote

# Allow importing awdui-server detection package
_ROOT = Path(__file__).resolve().parents[1] / "mcp-servers" / "awdui-server"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from detection import repo_store

app = FastAPI(title="AwdUI Repo Studio", version="1.0.0")


@app.on_event("startup")
def _startup_consolidate():
    try:
        from detection.repo_consolidate import maybe_auto_consolidate

        maybe_auto_consolidate()
    except Exception:
        pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8765",
        "http://127.0.0.1:8765",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class IdentificationModel(BaseModel):
    mandatory: dict[str, str] = Field(default_factory=dict)
    assistive: dict[str, str] = Field(default_factory=dict)
    smart: dict[str, str] = Field(default_factory=dict)
    ordinal: dict[str, str] = Field(default_factory=dict)


class ObjectUpdate(BaseModel):
    logical_name: Optional[str] = None
    identification: Optional[IdentificationModel] = None
    agent_hints: Optional[str] = None
    full_properties: Optional[dict[str, Any]] = None


class AppUpdate(BaseModel):
    app_name: Optional[str] = None
    exe_path: Optional[str] = None
    framework: Optional[str] = None
    agent_hints: Optional[str] = None


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/changes")
def repo_changes():
    return repo_store.get_repo_revision()


@app.get("/api/apps")
def list_apps():
    try:
        from detection.repo_consolidate import maybe_auto_consolidate

        maybe_auto_consolidate()
    except Exception:
        pass
    try:
        from detection.repo_framework import maybe_refresh_unknown_frameworks

        maybe_refresh_unknown_frameworks()
    except Exception:
        pass
    return {"apps": repo_store.list_applications()}


@app.get("/api/apps/{app_id}")
def get_app(app_id: str):
    try:
        from detection.repo_framework import refresh_app_framework

        refresh_app_framework(app_id)
    except Exception:
        pass
    app = repo_store.get_application(app_id)
    if not app:
        raise HTTPException(404, f"Application not found: {app_id}")
    return {"app": app}


@app.post("/api/apps/{app_id}/detect-framework")
def detect_app_framework(app_id: str, force: bool = False, window_title: str = ""):
    from detection.repo_framework import refresh_app_framework

    result = refresh_app_framework(
        app_id,
        window_title=window_title or None,
        force=force,
    )
    if not result.get("success"):
        raise HTTPException(404, result.get("error", "Detection failed"))
    app = repo_store.get_application(app_id)
    return {"app": app, "detection": result}


@app.put("/api/apps/{app_id}")
def update_app(app_id: str, body: AppUpdate):
    app = repo_store.update_application(
        app_id,
        app_name=body.app_name,
        exe_path=body.exe_path,
        framework=body.framework,
        agent_hints=body.agent_hints,
    )
    if not app:
        raise HTTPException(404, f"Application not found: {app_id}")
    return {"app": app}


@app.delete("/api/apps/{app_id}")
def delete_app(app_id: str, clear_assets: bool = True):
    result = repo_store.delete_application(app_id, clear_assets=clear_assets)
    if not result:
        raise HTTPException(404, f"Application not found: {app_id}")
    return result


@app.get("/api/apps/{app_id}/tree")
def app_tree(app_id: str):
    tree = repo_store.get_app_tree(app_id)
    if tree.get("error"):
        raise HTTPException(404, tree["error"])
    return tree


@app.get("/api/objects")
def get_object(repo_path: str):
    path = unquote(repo_path)
    obj = repo_store.get_object_by_path(path)
    if not obj:
        raise HTTPException(404, f"Object not found: {path}")
    hints = repo_store.get_agent_hints(path)
    return {"object": obj, "agent_hints": hints}


@app.put("/api/objects/{repo_path:path}")
def update_object(repo_path: str, body: ObjectUpdate):
    path = unquote(repo_path)
    ident = body.identification.model_dump() if body.identification else None
    obj = repo_store.update_object(
        path,
        logical_name=body.logical_name,
        identification=ident,
        agent_hints=body.agent_hints,
        full_properties=body.full_properties,
    )
    if not obj:
        raise HTTPException(404, f"Object not found: {path}")
    return {"object": obj}


@app.delete("/api/objects/{repo_path:path}")
def delete_object(repo_path: str):
    path = unquote(repo_path)
    if not repo_store.delete_object(path):
        raise HTTPException(404, f"Object not found: {path}")
    return {"deleted": True, "repo_path": path}


@app.get("/api/search")
def search(q: str = ""):
    if not q.strip():
        return {"results": []}
    return {"results": repo_store.search_objects(q.strip())}


@app.post("/api/migrate")
def migrate(force: bool = False):
    repo_store.reset_migration_flag()
    result = repo_store.migrate_json_repos(force=force)
    return result


@app.post("/api/consolidate")
def consolidate():
    from detection.repo_consolidate import consolidate_repositories

    return consolidate_repositories()


@app.post("/api/reset")
def reset_repo(clear_assets: bool = True):
    return repo_store.reset_repository(clear_assets=clear_assets)


@app.get("/api/hints/{repo_path:path}")
def hints(repo_path: str):
    path = unquote(repo_path)
    return {"repo_path": path, "hints": repo_store.get_agent_hints(path)}


_ASSETS = repo_store.assets_root()


@app.get("/api/assets/{asset_path:path}")
def serve_asset(asset_path: str):
    rel = asset_path.replace("\\", "/").lstrip("/")
    root = _ASSETS.resolve()
    candidates = [rel, repo_store.normalize_asset_rel(rel)]
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        path = (root / candidate).resolve()
        if path.is_file() and str(path).startswith(str(root)):
            return FileResponse(path)
    raise HTTPException(404, f"Asset not found: {asset_path}")


# Serve built SPA when dist exists
_DIST = Path(__file__).resolve().parent.parent / "repo-web" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="spa")

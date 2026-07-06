"""AwdUI auto-update from GitHub Release zip assets."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# --- update-config (PLACEHOLDERS.md) ---
UPDATE_CONFIG = {
    "package_name": "awdui-mcp",
    "display_name": "AwdUI",
    "repo_slug": os.environ.get("AWDUI_GITHUB_REPO", "aostapow/AwdUI-MCP"),
    "cache_dir_name": "awdui-mcp",
    "zip_asset_prefix": "AwdUI-MCP",
    "env_prefix": "AWDUI",
    "server_entry": "mcp-servers/awdui-server/server.py",
    "preserve_on_merge": [".env"],
}

DEFAULT_RELEASES_URL = (
    f"https://api.github.com/repos/{UPDATE_CONFIG['repo_slug']}/releases/latest"
)

_VERSION_RE = re.compile(r"^v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:[-+].*)?$")
DOWNLOAD_TIMEOUT_S = 120
CHECK_TIMEOUT_S = 30
LOCK_STALE_S = 10 * 60


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _env_var(suffix: str) -> str:
    return f"{UPDATE_CONFIG['env_prefix']}_{suffix}"


def env_flag_enabled(name: str, default: bool = True) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in ("false", "0")


def auto_update_enabled() -> bool:
    return env_flag_enabled(_env_var("AUTO_UPDATE"), True)


def update_check_enabled() -> bool:
    return env_flag_enabled(_env_var("UPDATE_CHECK"), True)


def get_update_config() -> dict[str, bool]:
    return {
        "enabled": update_check_enabled(),
        "auto_update": auto_update_enabled(),
    }


def get_cache_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        base = str(Path.home() / ".local" / "share")
    return Path(base) / UPDATE_CONFIG["cache_dir_name"]


def normalize_version(version: str) -> str:
    trimmed = version.strip().lstrip("vV")
    return trimmed.split("-")[0].split("+")[0]


def parse_version(version: str) -> tuple[int, int, int]:
    match = _VERSION_RE.match(version.strip())
    if not match:
        return (0, 0, 0)
    parts = [int(p) for p in match.groups() if p is not None]
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])  # type: ignore[return-value]


def is_newer_version(latest: str, current: str) -> bool:
    return parse_version(latest) > parse_version(current)


def zip_asset_file_name(version: str) -> str:
    prefix = UPDATE_CONFIG["zip_asset_prefix"]
    return f"{prefix}-v{normalize_version(version)}.zip"


def find_zip_asset(release_data: dict, version: str) -> Optional[dict[str, Any]]:
    assets = release_data.get("assets") or []
    if not assets:
        return None
    expected = zip_asset_file_name(version)
    exact = next((a for a in assets if a.get("name") == expected), None)
    candidate = exact or next(
        (a for a in assets if str(a.get("name", "")).lower().endswith(".zip")),
        None,
    )
    if not candidate or not candidate.get("browser_download_url"):
        return None
    return {
        "name": candidate["name"],
        "download_url": candidate["browser_download_url"],
        "size": candidate.get("size"),
    }


def read_local_version() -> str:
    version_file = _repo_root() / "VERSION"
    return version_file.read_text(encoding="utf-8").strip()


def read_last_applied() -> Optional[dict[str, str]]:
    path = get_cache_dir() / "last-applied.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("version"):
            return {
                "version": normalize_version(str(data["version"])),
                "appliedAt": str(data.get("appliedAt", "")),
            }
    except (OSError, json.JSONDecodeError, KeyError):
        pass
    return None


def write_last_applied(version: str) -> None:
    cache = get_cache_dir()
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / "last-applied.json"
    path.write_text(
        json.dumps(
            {
                "version": normalize_version(version),
                "appliedAt": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _log(level: str, message: str) -> None:
    sys.stderr.write(f"[{UPDATE_CONFIG['display_name']}:{level}] {message}\n")


def _github_get(url: str, timeout: int = CHECK_TIMEOUT_S) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{UPDATE_CONFIG['display_name']}/{read_local_version()}",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def _download_file(url: str, dest: Path, expected_size: Optional[int] = None) -> None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": UPDATE_CONFIG["display_name"]},
    )
    with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_S) as response:
        data = response.read()
    if expected_size and len(data) != expected_size:
        _log("update", f"WARN: download size {len(data)} differs from expected {expected_size}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)


def _acquire_lock() -> Optional[Path]:
    lock_path = get_cache_dir() / "update.lock"
    get_cache_dir().mkdir(parents=True, exist_ok=True)
    if lock_path.exists():
        age = datetime.now().timestamp() - lock_path.stat().st_mtime
        if age < LOCK_STALE_S:
            return None
        lock_path.unlink(missing_ok=True)
    lock_path.write_text(str(os.getpid()), encoding="utf-8")
    return lock_path


def _release_lock(lock_path: Optional[Path]) -> None:
    if lock_path and lock_path.exists():
        try:
            lock_path.unlink()
        except OSError:
            pass


def _copy_merge(src: Path, dest: Path, skip_names: set[str]) -> None:
    for entry in src.iterdir():
        if entry.name in skip_names:
            continue
        target = dest / entry.name
        if entry.is_dir():
            if target.exists() and target.is_file():
                target.unlink()
            _copy_merge(entry, target, skip_names)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(entry, target)


def _extract_zip(zip_path: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest_dir)
    children = list(dest_dir.iterdir())
    if len(children) == 1 and children[0].is_dir():
        inner = children[0]
        for item in list(inner.iterdir()):
            target = dest_dir / item.name
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
            shutil.move(str(item), str(dest_dir))
        inner.rmdir()


def _pip_install_requirements(install_dir: Path) -> None:
    req = install_dir / "mcp-servers" / "awdui-server" / "requirements.txt"
    if not req.is_file():
        return
    if sys.platform == "win32":
        pip = Path.home() / ".awdui-mcp" / ".venv" / "Scripts" / "pip.exe"
    else:
        pip = Path.home() / ".awdui-mcp" / ".venv" / "bin" / "pip"
    if not pip.is_file():
        _log("update", "venv pip not found — server will bootstrap deps on start")
        return
    result = subprocess.run(
        [str(pip), "install", "-q", "-r", str(req)],
        cwd=str(install_dir),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or f"pip install failed ({result.returncode})")


@dataclass
class UpdateResult:
    updated: bool
    reason: str = ""
    current: str = ""
    latest: str = ""
    previous: str = ""
    error: str = ""


def run_update(*, force: bool = False) -> UpdateResult:
    install_dir = _repo_root()
    current = read_local_version()

    if not force and not env_flag_enabled(_env_var("AUTO_UPDATE"), True):
        return UpdateResult(updated=False, reason="auto-update-disabled", current=current)
    if not force and not env_flag_enabled(_env_var("UPDATE_CHECK"), True):
        return UpdateResult(updated=False, reason="update-check-disabled", current=current)

    api_url = os.environ.get(_env_var("UPDATE_URL"), "").strip() or DEFAULT_RELEASES_URL

    try:
        release_data = _github_get(api_url)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        _log("update", f"ERROR: Update check failed: {exc}")
        return UpdateResult(updated=False, reason="check-failed", current=current, error=str(exc))

    tag = str(release_data.get("tag_name", "")).strip()
    latest = normalize_version(tag) if tag else ""
    if not latest:
        _log("update", "WARN: Could not determine latest version from release API")
        return UpdateResult(updated=False, reason="no-latest", current=current)

    if not is_newer_version(latest, current):
        return UpdateResult(updated=False, reason="already-current", current=current, latest=latest)

    last = read_last_applied()
    if not force and last and last.get("version") == latest:
        return UpdateResult(updated=False, reason="already-applied", current=current, latest=latest)

    zip_asset = find_zip_asset(release_data, latest)
    if not zip_asset:
        _log("update", f"WARN: No zip asset found for v{latest}")
        return UpdateResult(updated=False, reason="no-zip-asset", current=current, latest=latest)

    lock_path = _acquire_lock()
    if not lock_path:
        _log("update", "WARN: Another update is in progress, skipping")
        return UpdateResult(updated=False, reason="locked", current=current, latest=latest)

    temp_root = Path(tempfile.gettempdir()) / UPDATE_CONFIG["cache_dir_name"]
    zip_path = temp_root / f"download-v{latest}.zip"
    staging_dir = temp_root / f"staging-v{latest}"
    skip_merge = set(UPDATE_CONFIG.get("preserve_on_merge", [".env"]))

    try:
        _log("update", f"Updating from v{current} to v{latest}...")
        _download_file(zip_asset["download_url"], zip_path, zip_asset.get("size"))

        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        staging_dir.mkdir(parents=True, exist_ok=True)

        _extract_zip(zip_path, staging_dir)
        _copy_merge(staging_dir, install_dir, skip_merge)

        _log("update", "Installing Python dependencies...")
        _pip_install_requirements(install_dir)

        write_last_applied(latest)
        _log("update", f"Update complete — v{latest}")
    except Exception as exc:
        _log("update", f"ERROR: Update failed: {exc}. Continuing with current installation.")
        return UpdateResult(
            updated=False,
            reason="apply-failed",
            current=current,
            latest=latest,
            error=str(exc),
        )
    finally:
        _release_lock(lock_path)
        for p in (zip_path, staging_dir):
            if p.exists():
                shutil.rmtree(p, ignore_errors=True)

    return UpdateResult(updated=True, previous=current, latest=latest, current=latest)


def fetch_release_info(force: bool = False) -> dict[str, Any]:
    """Fetch latest release metadata for get_server_info / check_version."""
    import version_check

    info = version_check.check_version(force=force)
    api_url = os.environ.get(_env_var("UPDATE_URL"), "").strip() or DEFAULT_RELEASES_URL
    release_notes = None
    zip_asset_url = None
    try:
        release_data = _github_get(api_url)
        release_notes = release_data.get("body")
        if info.update_available:
            asset = find_zip_asset(release_data, info.latest_version)
            if asset:
                zip_asset_url = asset["download_url"]
    except Exception:
        pass
    return {
        "current_version": info.current_version,
        "latest_version": info.latest_version,
        "update_available": info.update_available,
        "release_url": info.release_url,
        "release_notes": release_notes,
        "zip_asset_url": zip_asset_url,
        "source": info.source,
    }


def get_server_info() -> dict[str, Any]:
    cfg = get_update_config()
    release = fetch_release_info(force=False)
    last = read_last_applied()
    root = _repo_root()
    return {
        "mcpServerName": UPDATE_CONFIG["package_name"],
        "mcpServerVersion": release["current_version"],
        "pythonVersion": sys.version.split()[0],
        "installPath": str(root),
        "updateAvailable": release["update_available"],
        "latestVersion": release["latest_version"] if release["update_available"] else release["latest_version"],
        "releaseUrl": release["release_url"],
        "releaseNotes": release.get("release_notes"),
        "zipAssetUrl": release.get("zip_asset_url"),
        "autoUpdateEnabled": cfg["auto_update"],
        "updateCheckEnabled": cfg["enabled"],
        "lastAppliedVersion": last.get("version") if last else None,
        "lastAppliedAt": last.get("appliedAt") if last else None,
        "updateCommand": "python scripts/update.py",
        "launcherEntryPoint": "scripts/launcher.py",
        "repository": f"https://github.com/{UPDATE_CONFIG['repo_slug']}",
    }

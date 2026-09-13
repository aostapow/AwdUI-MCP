"""Start AwdUI Object Repository Studio (API + built SPA) with the MCP."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path


def _env_flag(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in ("0", "false", "no", "off")


def _http_json(url: str, timeout: float = 1.5) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            if int(getattr(resp, "status", 200)) != 200:
                return None
            import json

            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _http_ok(url: str, timeout: float = 1.5) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return int(getattr(resp, "status", 200)) == 200
    except Exception:
        return False


def _api_healthy(port: int) -> bool:
    body = _http_json(f"http://127.0.0.1:{port}/api/health")
    if not body or not body.get("ok"):
        return False
    # Require catalog feature (api_version >= 2) so stale API processes get replaced.
    if body.get("api_version", 1) < 2:
        return False
    return _http_ok(f"http://127.0.0.1:{port}/api/catalog")


def _vite_healthy() -> bool:
    return _http_ok("http://127.0.0.1:5173/")


def _ensure_api_deps(python: str) -> None:
    subprocess.run(
        [python, "-m", "pip", "install", "-q", "fastapi", "uvicorn"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def _ensure_web_dist(root: Path) -> bool:
    dist = root / "repo-web" / "dist" / "index.html"
    if dist.is_file():
        return True
    npm = shutil.which("npm")
    if not npm:
        sys.stderr.write(
            "[AwdUI:repo-studio] SPA not built and npm not found. "
            "Open http://127.0.0.1:8765 after running scripts/start-repo-studio.ps1\n"
        )
        return False
    web = root / "repo-web"
    if not (web / "package.json").is_file():
        return False
    sys.stderr.write("[AwdUI:repo-studio] Building repo-web (first run)...\n")
    if not (web / "node_modules").is_dir():
        subprocess.run([npm, "install"], cwd=web, check=False)
    build = subprocess.run([npm, "run", "build"], cwd=web, check=False)
    return dist.is_file() if build.returncode == 0 else False


def _spawn_detached(cmd: list[str], *, cwd: Path | None = None) -> None:
    kwargs: dict = {
        "cwd": str(cwd) if cwd else None,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = (
            subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
        )
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(cmd, **kwargs)


def _kill_listener(port: int) -> None:
    """Stop process listening on port (Windows/Linux) so we can restart stale API."""
    if sys.platform == "win32":
        try:
            out = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                check=False,
            )
            for line in (out.stdout or "").splitlines():
                if f":{port} " in line and "LISTENING" in line.upper():
                    parts = line.split()
                    if parts:
                        pid = parts[-1]
                        if pid.isdigit() and int(pid) > 0:
                            subprocess.run(
                                ["taskkill", "/F", "/PID", pid],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                check=False,
                            )
        except Exception:
            pass
        return
    try:
        subprocess.run(
            ["fuser", "-k", f"{port}/tcp"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except Exception:
        pass


def _start_api(root: Path, python: str, port: int) -> None:
    api_dir = root / "repo-api"
    _spawn_detached(
        [
            python,
            "-m",
            "uvicorn",
            "main:app",
            "--app-dir",
            str(api_dir),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=root,
    )


def _start_vite_dev(root: Path) -> None:
    npm = shutil.which("npm")
    if not npm:
        return
    web = root / "repo-web"
    if not (web / "package.json").is_file():
        return
    if not (web / "node_modules").is_dir():
        subprocess.run([npm, "install"], cwd=web, check=False)
    _spawn_detached([npm, "run", "dev"], cwd=web)


def maybe_start_repo_studio(root: Path, python: str | None = None) -> None:
    """Start Repo Studio API (and optional Vite dev) if not already running."""
    if not _env_flag("AWDUI_REPO_STUDIO", default=True):
        return

    py = python or sys.executable
    port = int(os.environ.get("AWDUI_REPO_PORT", "8765"))
    dev = _env_flag("AWDUI_REPO_DEV", default=False)

    if _api_healthy(port):
        sys.stderr.write(f"[AwdUI:repo-studio] API already running on :{port}\n")
    else:
        if _http_ok(f"http://127.0.0.1:{port}/api/health"):
            sys.stderr.write(
                f"[AwdUI:repo-studio] Stale API on :{port} (missing catalog) — restarting\n"
            )
            _kill_listener(port)
            import time

            time.sleep(0.5)
        _ensure_api_deps(py)
        _ensure_web_dist(root)
        _start_api(root, py, port)
        sys.stderr.write(
            f"[AwdUI:repo-studio] Started API http://127.0.0.1:{port}\n"
        )

    if dev:
        if _vite_healthy():
            sys.stderr.write("[AwdUI:repo-studio] Vite already running on :5173\n")
        else:
            _start_vite_dev(root)
            sys.stderr.write(
                "[AwdUI:repo-studio] Started Vite http://localhost:5173\n"
            )
    elif _ensure_web_dist(root) or _api_healthy(port):
        sys.stderr.write(
            f"[AwdUI:repo-studio] UI http://127.0.0.1:{port} "
            "(set AWDUI_REPO_DEV=1 for Vite hot-reload)\n"
        )

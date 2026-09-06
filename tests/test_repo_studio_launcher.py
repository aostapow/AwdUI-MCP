"""Tests for Repo Studio auto-start with MCP."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from repo_studio_launcher import maybe_start_repo_studio


@pytest.fixture
def root(tmp_path):
    api = tmp_path / "repo-api"
    api.mkdir()
    (api / "main.py").write_text("# api\n", encoding="utf-8")
    web = tmp_path / "repo-web"
    web.mkdir()
    (web / "package.json").write_text("{}", encoding="utf-8")
    dist = web / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html></html>", encoding="utf-8")
    return tmp_path


class TestRepoStudioLauncher:
    def test_disabled_by_env(self, root, monkeypatch):
        monkeypatch.setenv("AWDUI_REPO_STUDIO", "0")
        called = {"api": False}

        def fake_start(*_a, **_k):
            called["api"] = True

        monkeypatch.setattr("repo_studio_launcher._start_api", fake_start)
        maybe_start_repo_studio(root, python=sys.executable)
        assert called["api"] is False

    def test_skips_when_api_already_up(self, root, monkeypatch):
        monkeypatch.delenv("AWDUI_REPO_STUDIO", raising=False)
        called = {"api": False}

        monkeypatch.setattr("repo_studio_launcher._api_healthy", lambda _p: True)
        monkeypatch.setattr(
            "repo_studio_launcher._start_api",
            lambda *_a, **_k: called.__setitem__("api", True),
        )
        maybe_start_repo_studio(root, python=sys.executable)
        assert called["api"] is False

    def test_starts_api_when_down(self, root, monkeypatch):
        monkeypatch.delenv("AWDUI_REPO_STUDIO", raising=False)
        started: list[int] = []

        monkeypatch.setattr("repo_studio_launcher._api_healthy", lambda _p: False)
        monkeypatch.setattr("repo_studio_launcher._ensure_api_deps", lambda _p: None)
        monkeypatch.setattr("repo_studio_launcher._ensure_web_dist", lambda _r: True)
        monkeypatch.setattr(
            "repo_studio_launcher._start_api",
            lambda _r, _py, port: started.append(port),
        )
        maybe_start_repo_studio(root, python=sys.executable)
        assert started == [8765]

    def test_dev_starts_vite(self, root, monkeypatch):
        monkeypatch.setenv("AWDUI_REPO_DEV", "1")
        vite = {"called": False}

        monkeypatch.setattr("repo_studio_launcher._api_healthy", lambda _p: True)
        monkeypatch.setattr("repo_studio_launcher._vite_healthy", lambda: False)
        monkeypatch.setattr(
            "repo_studio_launcher._start_vite_dev",
            lambda _r: vite.__setitem__("called", True),
        )
        maybe_start_repo_studio(root, python=sys.executable)
        assert vite["called"] is True

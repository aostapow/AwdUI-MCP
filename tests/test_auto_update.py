"""Tests for AwdUI auto-update helpers."""
from __future__ import annotations


class TestVersionUtils:
    def test_normalize_version(self):
        from auto_update import normalize_version
        assert normalize_version("v1.2.3") == "1.2.3"
        assert normalize_version("1.2.3-beta") == "1.2.3"

    def test_is_newer_version(self):
        from auto_update import is_newer_version
        assert is_newer_version("1.2.0", "1.1.9")
        assert not is_newer_version("1.0.0", "1.0.0")

    def test_zip_asset_file_name(self):
        from auto_update import zip_asset_file_name
        assert zip_asset_file_name("1.2.3") == "AwdUI-MCP-v1.2.3.zip"

    def test_find_zip_asset_exact(self):
        from auto_update import find_zip_asset
        data = {
            "assets": [
                {"name": "AwdUI-MCP-v2.0.0.zip", "browser_download_url": "https://example.com/a.zip", "size": 100},
            ]
        }
        asset = find_zip_asset(data, "2.0.0")
        assert asset is not None
        assert asset["name"] == "AwdUI-MCP-v2.0.0.zip"


class TestGetServerInfo:
    def test_get_server_info_shape(self, monkeypatch):
        from auto_update import get_server_info

        monkeypatch.setattr(
            "auto_update.fetch_release_info",
            lambda force=False: {
                "current_version": "0.1.0",
                "latest_version": "0.1.0",
                "update_available": False,
                "release_url": "https://github.com/aostapow/AwdUI-MCP/releases",
                "release_notes": None,
                "zip_asset_url": None,
                "source": "release",
            },
        )
        monkeypatch.setattr("auto_update.read_last_applied", lambda: None)

        info = get_server_info()
        assert info["mcpServerName"] == "awdui-mcp"
        assert info["mcpServerVersion"] == "0.1.0"
        assert info["launcherEntryPoint"] == "scripts/launcher.py"
        assert info["updateCommand"] == "python scripts/update.py"


class TestRunUpdate:
    def test_auto_update_disabled(self, monkeypatch):
        from auto_update import run_update

        monkeypatch.setenv("AWDUI_AUTO_UPDATE", "false")
        result = run_update(force=False)
        assert result.updated is False
        assert result.reason == "auto-update-disabled"

    def test_already_current(self, monkeypatch):
        from auto_update import run_update

        monkeypatch.setenv("AWDUI_AUTO_UPDATE", "true")
        monkeypatch.setenv("AWDUI_UPDATE_CHECK", "true")
        monkeypatch.setattr("auto_update.read_local_version", lambda: "9.9.9")
        monkeypatch.setattr(
            "auto_update._github_get",
            lambda url: {"tag_name": "v9.9.9", "assets": []},
        )
        result = run_update(force=False)
        assert result.reason == "already-current"

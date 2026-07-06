"""Version tools -- installed version, update checks, and server introspection."""

from __future__ import annotations

import json

import version_check


def register(server) -> int:
    """Register version tools on *server*. Returns the number of tools registered."""

    @server.tool()
    def check_version(force: bool = False) -> str:
        """Check whether a newer AwdUI version is available on GitHub.

        Parameters:
            force: When true, bypass the 24-hour cache and query GitHub now.
        """
        info = version_check.check_version(force=force)
        lines = [
            f"current: v{info.current_version}",
            f"latest: v{info.latest_version} ({info.source})",
            f"status: {'update available' if info.update_available else 'up to date'}",
            f"url: {info.release_url}",
        ]
        if info.update_available:
            lines.append(
                "update: python scripts/update.py in your AwdUI install, then restart the MCP client"
            )
        return "\n".join(lines)

    @server.tool()
    def get_server_info() -> str:
        """Returns MCP server version, runtime info, and whether a newer release is available on GitHub."""
        from auto_update import get_server_info as _info
        return json.dumps(_info(), indent=2)

    return 2

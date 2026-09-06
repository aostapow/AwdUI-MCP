"""Purge host/noise applications from the object repository."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp-servers" / "awdui-server"))

from detection.auto_repo import HOST_REPO_BLOCKLIST, is_blocked_repo_app
from detection.repo_store import _connect, _ensure_migrated, delete_application


def purge_blocked_applications() -> list[dict]:
    _ensure_migrated()
    results: list[dict] = []
    with _connect() as conn:
        apps = conn.execute(
            "SELECT app_id, app_name, exe_path FROM applications ORDER BY app_name"
        ).fetchall()
    for row in apps:
        name = row["app_name"] or ""
        exe = row["exe_path"] or ""
        if not is_blocked_repo_app(name, exe):
            continue
        out = delete_application(name, exe, app_id_value=row["app_id"])
        out["reason"] = "host_blocklist"
        results.append(out)
    return results


if __name__ == "__main__":
    purged = purge_blocked_applications()
    if not purged:
        print("No blocked applications found in repository.")
    else:
        for item in purged:
            if item.get("success"):
                print(
                    f"Removed {item.get('app_name')} "
                    f"({item.get('objects_removed', 0)} objects)"
                )
            else:
                print(f"Skip {item}")

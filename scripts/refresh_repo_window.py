"""Refresh repository snapshots for all capturable controls in a window."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "mcp-servers" / "awdui-server"
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))


def _focus(window_title: str) -> None:
    from tools.windows import find_matching_window, do_list_windows

    match = find_matching_window(window_title, do_list_windows())
    win = match.get("window") or {}
    hwnd = int(win.get("hwnd") or 0)
    if hwnd:
        try:
            from awdui_platform.win32_backend import set_foreground_window

            set_foreground_window(hwnd)
            time.sleep(0.15)
        except Exception:
            pass


def _list_capturable(window_title: str, max_depth: int = 12) -> list[dict]:
    from tools.ui_automation import do_list_elements

    result = do_list_elements(
        window_title=window_title,
        max_depth=max_depth,
        include_offscreen=False,
    )
    items: list[dict] = []
    for elem in result.get("elements", []):
        aid = (elem.get("automation_id") or "").strip()
        w = int(elem.get("width") or 0)
        h = int(elem.get("height") or 0)
        if not aid or w <= 0 or h <= 0:
            continue
        items.append(elem)
    return items


def _window_key(window_title: str) -> str:
    import re

    raw = (window_title or "main").strip()
    token = raw.split(" - ")[0].split("|")[0].strip()
    safe = re.sub(r"[^\w\-]", "_", token)
    return (safe or "main")[:48]


def _remember_fresh(elem: dict, *, window_title: str, repo_path: str) -> str | None:
    """Upsert using the same spy screen bbox as highlight_rect."""
    from detection.object_repository import load_repo, upsert_object
    from detection.object_snapshot import capture_element_crop
    from detection.winforms_map import build_identification, infer_swf_class
    from tools.framework_detect import do_detect_framework

    fw = do_detect_framework(window_title)
    app_name = fw.get("process_name") or fw.get("exe_name") or "foreground"
    exe_path = fw.get("exe_path", "")
    repo = load_repo(app_name, exe_path)
    repo["exe_path"] = exe_path

    snapshots = capture_element_crop(
        elem,
        repo_path=repo_path,
        app_id=repo["app_id"],
        window_title=window_title,
        fresh=True,
        verify=False,
    )
    if not snapshots:
        raise RuntimeError("capture failed")
    bbox = snapshots["latest"]["bbox"]
    normalized = {
        **elem,
        "x": bbox["x"],
        "y": bbox["y"],
        "width": bbox["w"],
        "height": bbox["h"],
    }
    swf = infer_swf_class(normalized.get("role", ""), normalized.get("class_name", ""))
    upsert_object(
        repo,
        repo_path,
        obj_class=swf,
        element=normalized,
        identification=build_identification(normalized, swf),
        snapshots=snapshots,
        last_resolution={
            "layer": "native",
            "backend": normalized.get("backend", "uia"),
            "bbox": bbox,
        },
    )
    return repo_path


def refresh_window(
    window_title: str,
    *,
    max_depth: int = 12,
    dry_run: bool = False,
) -> dict:
    _focus(window_title)
    window_key = _window_key(window_title)
    elements = _list_capturable(window_title, max_depth=max_depth)

    captured: list[str] = []
    failed: list[dict] = []
    for elem in elements:
        aid = elem["automation_id"]
        repo_path = f"{window_key}/{aid}"
        if dry_run:
            captured.append(repo_path)
            continue
        try:
            path = _remember_fresh(
                elem,
                window_title=window_title,
                repo_path=repo_path,
            )
            if path:
                captured.append(path)
            else:
                failed.append({"repo_path": repo_path, "error": "remember returned None"})
        except Exception as exc:
            failed.append({"repo_path": repo_path, "error": str(exc)})

    return {
        "window_title": window_title,
        "window_key": window_key,
        "found": len(elements),
        "captured": len(captured),
        "failed": failed,
        "paths": captured,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("window_title", help="Partial window title, e.g. Calculadora")
    parser.add_argument("--max-depth", type=int, default=12)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    summary = refresh_window(
        args.window_title,
        max_depth=args.max_depth,
        dry_run=args.dry_run,
    )
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(
            f"{summary['window_title']}: {summary['captured']}/{summary['found']} captured"
        )
        for item in summary["failed"]:
            print(f"  FAIL {item['repo_path']}: {item['error']}")
    return 0 if not summary["failed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

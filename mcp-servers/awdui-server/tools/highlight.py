"""On-screen element highlight overlay (Automation Spy style red border)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

_OVERLAY_PROC = None


def _sidecar_path() -> Optional[Path]:
    p = Path(__file__).resolve().parents[2] / "awdui-spy-sidecar" / "publish" / "awdui-spy-sidecar.exe"
    if p.exists():
        return p
    return None


def _call_sidecar(command: str, params: dict) -> dict:
    exe = _sidecar_path()
    if not exe:
        return {"error": "spy sidecar not built"}
    req = json.dumps({"Command": command, "Params": params})
    try:
        proc = subprocess.run(
            [str(exe)],
            input=req,
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if proc.stdout.strip():
            return json.loads(proc.stdout.strip())
        return {"error": proc.stderr or "no output"}
    except Exception as exc:
        return {"error": str(exc)}


def _matches_element(
    props: dict,
    automation_id: str = "",
    name: str = "",
) -> bool:
    if automation_id and props.get("automation_id") == automation_id:
        return True
    if name and str(props.get("name", "")).lower() == name.lower():
        return True
    return False


def _bbox_hits_element(
    bbox: tuple[int, int, int, int],
    *,
    automation_id: str = "",
    name: str = "",
) -> bool:
    if not automation_id and not name:
        return True
    try:
        from tools.spy_bridge import spy_available, spy_inspect_at

        if not spy_available():
            return True
        x, y, w, h = bbox
        hit = spy_inspect_at(x + w // 2, y + h // 2)
        if not hit.get("found"):
            return True
        return _matches_element(hit.get("properties") or {}, automation_id, name)
    except Exception:
        return True


def _uia_list_bbox(
    *,
    automation_id: str = "",
    name: str = "",
    window_title: Optional[str] = None,
) -> Optional[tuple[int, int, int, int]]:
    """UIA/pywinauto BoundingRectangle — correct for UWP controls."""
    try:
        from tools.ui_automation import do_list_elements

        listed = do_list_elements(
            window_title=window_title or "",
            max_depth=12,
            include_offscreen=False,
        ).get("elements", [])
        for candidate in listed:
            aid = (candidate.get("automation_id") or "").strip()
            cname = (candidate.get("name") or "").strip()
            if automation_id and aid != automation_id:
                continue
            if not automation_id and name and cname.lower() != name.lower():
                continue
            if not automation_id and not name:
                continue
            x = int(candidate.get("x", 0) or 0)
            y = int(candidate.get("y", 0) or 0)
            w = int(candidate.get("width") or candidate.get("w") or 0)
            h = int(candidate.get("height") or candidate.get("h") or 0)
            if w > 0 and h > 0:
                return x, y, w, h
    except Exception:
        pass
    return None


def element_screen_bbox(
    elem: dict,
    *,
    window_title: Optional[str] = None,
    repo_path: Optional[str] = None,
) -> Optional[tuple[int, int, int, int]]:
    """Physical screen rectangle for highlight and repository crops."""
    aid = (elem.get("automation_id") or "").strip()
    name = (elem.get("name") or "").strip()
    if not aid and repo_path:
        leaf = repo_path.rsplit("/", 1)[-1]
        if leaf and leaf not in ("main",):
            aid = leaf

    uia_bbox = _uia_list_bbox(
        automation_id=aid,
        name=name,
        window_title=window_title,
    )
    if uia_bbox:
        return uia_bbox

    try:
        from tools.spy_bridge import spy_available, spy_inspect_element

        if spy_available() and (aid or name):
            result = spy_inspect_element(
                name=name,
                automation_id=aid,
                window_title=window_title or "",
            )
            if result.get("found"):
                p = result.get("properties") or {}
                x = int(p.get("x", 0) or 0)
                y = int(p.get("y", 0) or 0)
                w = int(p.get("width") or 0)
                h = int(p.get("height") or 0)
                if w > 0 and h > 0:
                    if _bbox_hits_element((x, y, w, h), automation_id=aid, name=name):
                        return x, y, w, h
                    region = None
                    try:
                        from detection.element_coords import window_region

                        region = window_region(window_title)
                    except Exception:
                        pass
                    if region:
                        sx = x + int(region["x"])
                        sy = y + int(region["y"])
                        offset_bbox = (sx, sy, w, h)
                        if _bbox_hits_element(offset_bbox, automation_id=aid, name=name):
                            return offset_bbox
    except Exception:
        pass

    x = int(elem.get("x", 0) or 0)
    y = int(elem.get("y", 0) or 0)
    w = int(elem.get("width") or elem.get("w") or 0)
    h = int(elem.get("height") or elem.get("h") or 0)
    if w <= 0 or h <= 0:
        return None
    if window_title:
        from detection.element_coords import to_screen_coords

        norm = to_screen_coords(
            {"x": x, "y": y, "width": w, "height": h},
            window_title,
        )
        return (
            int(norm["x"]),
            int(norm["y"]),
            int(norm["width"]),
            int(norm["height"]),
        )
    return x, y, w, h


def highlight_rect(
    x: int, y: int, w: int, h: int,
    *,
    duration_ms: int = 3000,
    color: str = "red",
) -> dict:
    """Draw red border overlay around rectangle."""
    global _OVERLAY_PROC
    result = _call_sidecar("highlight", {
        "x": x, "y": y, "w": w, "h": h,
        "duration_ms": duration_ms,
        "color": color,
    })
    if "error" in result and sys.platform == "win32":
        return _highlight_win32_fallback(x, y, w, h, duration_ms)
    return result


def clear_highlight() -> dict:
    return _call_sidecar("unhighlight", {})


def highlight_element_dict(
    elem: dict,
    duration_ms: int = 3000,
    *,
    window_title: Optional[str] = None,
    repo_path: Optional[str] = None,
) -> dict:
    bbox = element_screen_bbox(elem, window_title=window_title, repo_path=repo_path)
    if not bbox:
        return {"error": "element has no bounding box"}
    x, y, w, h = bbox
    return highlight_rect(x, y, w, h, duration_ms=duration_ms)


def _highlight_win32_fallback(x: int, y: int, w: int, h: int, duration_ms: int) -> dict:
    """Python-only fallback: flash via screenshot annotation path (no overlay)."""
    try:
        from PIL import Image, ImageDraw
        from tools.screenshot import capture_screenshot
        from tools.image_utils import load_image_from_screenshot

        shot = capture_screenshot()
        img = load_image_from_screenshot(shot)
        draw = ImageDraw.Draw(img)
        thickness = 3
        for i in range(thickness):
            draw.rectangle(
                [x - i, y - i, x + w + i, y + h + i],
                outline=(255, 0, 0),
            )
        out = Path(shot["path"]).with_name("highlight_annotated.png")
        img.save(out)
        return {"annotated_path": str(out), "fallback": True, "duration_ms": duration_ms}
    except Exception as exc:
        return {"error": str(exc)}

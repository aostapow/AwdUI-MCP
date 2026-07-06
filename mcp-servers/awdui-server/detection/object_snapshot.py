"""Post-interaction object snapshot — element crop + optional full assets."""
from __future__ import annotations

import hashlib
import re
import time
from typing import Any, Optional

from detection.object_repository import assets_path, load_repo, relative_asset, upsert_object


def _phash(img) -> str:
    try:
        import numpy as np
        small = img.resize((8, 8)).convert("L")
        arr = np.array(small, dtype=float)
        avg = arr.mean()
        bits = (arr > avg).flatten()
        return hashlib.md5(bits.tobytes()).hexdigest()[:16]
    except Exception:
        return ""


def _grab_virtual_screen() -> tuple[Any, int, int]:
    import mss
    from PIL import Image

    with mss.mss() as sct:
        mon = sct.monitors[0]
        shot = sct.grab(mon)
        img = Image.frombytes("RGB", shot.size, shot.rgb)
        return img, int(mon["left"]), int(mon["top"])


def _element_bbox(elem: dict) -> tuple[int, int, int, int] | None:
    x = int(elem.get("x", 0) or 0)
    y = int(elem.get("y", 0) or 0)
    w = int(elem.get("width") or elem.get("w") or 0)
    h = int(elem.get("height") or elem.get("h") or 0)
    if w <= 0 or h <= 0:
        return None
    return x, y, w, h


def _resolve_live_bbox(
    elem: dict,
    *,
    window_title: Optional[str] = None,
    repo_path: Optional[str] = None,
) -> dict:
    """Re-query Spy for a fresh bounding box (same engine as find/click)."""
    aid = (elem.get("automation_id") or "").strip()
    name = (elem.get("name") or "").strip()
    if not aid and repo_path:
        leaf = repo_path.rsplit("/", 1)[-1]
        if leaf and leaf not in ("main",):
            aid = leaf
    try:
        from tools.spy_bridge import spy_available, spy_inspect_element, spy_props_to_element

        if spy_available() and (aid or name):
            result = spy_inspect_element(
                name=name,
                automation_id=aid,
                window_title=window_title or "",
            )
            if result.get("found"):
                live = spy_props_to_element(
                    result.get("properties") or {}, window_title=window_title
                )
                if _element_bbox(live):
                    return live
    except Exception:
        pass
    return elem


def _crop_on_image(img, x: int, y: int, w: int, h: int):
    x1 = max(0, x)
    y1 = max(0, y)
    x2 = min(img.width, x + w)
    y2 = min(img.height, y + h)
    if x2 <= x1 or y2 <= y1:
        return None
    return img.crop((x1, y1, x2, y2))


def _screen_crop(bbox: tuple[int, int, int, int]):
    x, y, w, h = bbox
    screen, origin_x, origin_y = _grab_virtual_screen()
    return _crop_on_image(screen, x - origin_x, y - origin_y, w, h)


def _window_crop(bbox: tuple[int, int, int, int], window_title: str):
    from tools.screenshot import _capture_window_by_title

    win_img = _capture_window_by_title(window_title)
    if win_img is None:
        return None
    return _crop_on_image(win_img, *bbox)


def _verify_crop(
    crop,
    screen_bbox: tuple[int, int, int, int],
    expected_automation_id: str = "",
    expected_name: str = "",
) -> bool:
    if crop is None or crop.width < 4 or crop.height < 4:
        return False
    if not expected_automation_id and not expected_name:
        return True
    try:
        import numpy as np

        arr = np.array(crop.convert("L"), dtype=float)
        if float(arr.std()) < 2.0:
            return False
    except Exception:
        pass
    try:
        from tools.spy_bridge import spy_available, spy_inspect_at

        if not spy_available():
            return True
        x, y, w, h = screen_bbox
        hit = spy_inspect_at(x + w // 2, y + h // 2)
        if not hit.get("found"):
            return True
        props = hit.get("properties") or {}
        if expected_automation_id and props.get("automation_id") == expected_automation_id:
            return True
        if expected_name and str(props.get("name", "")).lower() == expected_name.lower():
            return True
        return False
    except Exception:
        return True


def _capture_element_image(
    elem: dict,
    *,
    window_title: Optional[str] = None,
    repo_path: Optional[str] = None,
    fresh: bool = False,
    verify: bool = True,
):
    """Return (PIL crop, screen bbox) or None."""
    from tools.highlight import element_screen_bbox

    if fresh:
        screen = element_screen_bbox(elem, window_title=window_title, repo_path=repo_path)
    else:
        live = _resolve_live_bbox(elem, window_title=window_title, repo_path=repo_path)
        screen = element_screen_bbox(live, window_title=window_title, repo_path=repo_path)
    if not screen:
        return None

    aid = (elem.get("automation_id") or "").strip()
    name = (elem.get("name") or "").strip()
    crop = _screen_crop(screen)
    if crop is None:
        return None
    if not verify:
        return crop, screen
    if _verify_crop(crop, screen, aid, name):
        return crop, screen
    return crop, screen


def _crop_filename(repo_path: str) -> str:
    safe = re.sub(r"[^\w\-]", "_", repo_path.replace("/", "_").replace("\\", "_"))[:96]
    return f"{safe}_crop.png"


def capture_element_crop(
    elem: dict,
    *,
    repo_path: str,
    app_id: str,
    window_title: Optional[str] = None,
    fresh: bool = False,
    verify: bool = True,
) -> Optional[dict]:
    crop_result = _capture_element_image(
        elem,
        window_title=window_title,
        repo_path=repo_path,
        fresh=fresh,
        verify=verify,
    )
    if crop_result is None:
        return None
    crop, screen = crop_result
    x, y, w, h = screen

    fname = _crop_filename(repo_path)
    crop.save(assets_path(app_id, fname), format="PNG")

    snapshot = {
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "images": {"crop": relative_asset(app_id, fname)},
        "phash": _phash(crop),
        "bbox": {"x": x, "y": y, "w": w, "h": h},
    }
    return {"latest": snapshot}


def capture_object_snapshot(
    elem: dict,
    *,
    window_title: Optional[str] = None,
    repo_path: Optional[str] = None,
    app_name: str = "foreground",
    exe_path: str = "",
    full_properties: Optional[dict] = None,
    highlight: bool = False,
) -> dict:
    from PIL import Image, ImageDraw

    repo = load_repo(app_name, exe_path)
    repo["exe_path"] = exe_path
    app_id = repo["app_id"]
    path = repo_path or elem.get("name") or "object"

    crop_result = _capture_element_image(elem, window_title=window_title, repo_path=repo_path)
    if crop_result is None:
        return {"error": "capture failed"}
    crop, bbox = crop_result
    px, py, pw, ph = bbox
    x, y, w, h = px, py, pw, ph

    screen, origin_x, origin_y = _grab_virtual_screen()
    live = _resolve_live_bbox(elem, window_title=window_title, repo_path=repo_path)
    sx, sy = px - origin_x, py - origin_y

    pad = max(4, int(min(pw, ph) * 0.2))
    context = screen.crop((
        max(0, sx - pad),
        max(0, sy - pad),
        min(screen.width, sx + pw + pad),
        min(screen.height, sy + ph + pad),
    ))
    template = crop.copy()

    annotated = screen.copy()
    draw = ImageDraw.Draw(annotated)
    for i in range(3):
        draw.rectangle([sx - i, sy - i, sx + pw + i, sy + ph + i], outline=(255, 0, 0))

    base = path.replace("/", "_")
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in base)[:64]
    ts = int(time.time())
    names = {
        "crop": _crop_filename(path) if repo_path else f"{safe}_{ts}_crop.png",
        "context": f"{safe}_{ts}_context.png",
        "template": f"{safe}_{ts}_template.png",
        "annotated": f"{safe}_{ts}_annotated.png",
    }
    paths = {}
    for key, fname in names.items():
        p = assets_path(app_id, fname)
        {"crop": crop, "context": context, "template": template, "annotated": annotated}[key].save(p)
        paths[key] = relative_asset(app_id, fname)

    if not full_properties:
        full_properties = dict(live)
        try:
            from tools.spy_bridge import spy_inspect_at
            spy = spy_inspect_at(px + pw // 2, py + ph // 2)
            if spy.get("found"):
                full_properties = spy.get("properties", full_properties)
        except Exception:
            pass

    snapshot = {
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "full_properties": full_properties,
        "images": paths,
        "phash": _phash(template),
        "bbox": {"x": x, "y": y, "w": w, "h": h},
    }

    if repo_path:
        from detection.object_repository import parse_repo_path
        from detection.winforms_map import infer_swf_class, build_identification
        try:
            _, chain = parse_repo_path(repo_path)
            parent = chain[-2] if len(chain) > 1 else ""
        except ValueError:
            parent = ""
        swf_class = infer_swf_class(elem.get("role", ""), elem.get("class_name", ""))
        upsert_object(
            repo,
            repo_path,
            obj_class=swf_class,
            parent=parent,
            element=elem,
            identification=build_identification(elem, swf_class),
            snapshots={"latest": snapshot},
            last_resolution={
                "layer": elem.get("backend", "uia"),
                "backend": elem.get("backend", "uia"),
                "bbox": snapshot["bbox"],
            },
        )
    if highlight:
        try:
            from tools.highlight import highlight_rect
            highlight_rect(px, py, pw, ph)
        except Exception:
            pass

    return {"snapshot": snapshot, "app_id": app_id}

"""Layered detection orchestrator — repo → memory → native → OCR → visual → agentic."""
from __future__ import annotations

import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from detection.element_model import DetectedElement, dict_to_legacy_element
from detection.layers.scoring import dedupe_elements, score_element_match
from detection.object_repository import load_repo, upsert_object, parse_repo_path
from detection.strategy_memory import get_strategy, make_key, record_miss, record_success
from detection.winforms_map import build_identification, infer_swf_class

_MIN_NAMED_ELEMENTS = 5
_MIN_AVG_CONFIDENCE = 0.4


@dataclass
class LocatorQuery:
  name: Optional[str] = None
  role: Optional[str] = None
  automation_id: Optional[str] = None
  class_name: Optional[str] = None
  window_title: Optional[str] = None
  repo_path: Optional[str] = None
  index: int = 0


@dataclass
class ResolveOptions:
  strict: bool = False
  timeout_ms: int = 5000
  agentic: bool = False
  remember: bool = True
  highlight: bool = False
  backend: Optional[str] = None


@dataclass
class ResolveResult:
  found: bool = False
  layer: str = ""
  backend: str = ""
  method: str = ""
  confidence: float = 0.0
  elements: list[dict] = field(default_factory=list)
  repo_updated: bool = False
  repo_path: Optional[str] = None
  trace_id: str = ""
  error: str = ""
  agentic_context: Optional[dict] = None

  def to_dict(self) -> dict:
    d: dict[str, Any] = {
      "found": self.found,
      "layer": self.layer,
      "backend": self.backend or self.method,
      "method": self.method or self.backend,
      "confidence": self.confidence,
      "elements": self.elements,
      "repo_updated": self.repo_updated,
      "trace_id": self.trace_id,
    }
    if self.repo_path:
      d["repo_path"] = self.repo_path
    if self.error:
      d["error"] = self.error
    if self.agentic_context:
      d["agentic_context"] = self.agentic_context
    return d


class LayeredDetector:
  """Multi-layer element resolution with memory and repository."""

  def __init__(self, orchestrator):
    self._orch = orchestrator

  def _app_context(self, window_title: Optional[str]) -> tuple[str, dict]:
    app_name = window_title or "foreground"
    exe_path = ""
    framework = "unknown"
    try:
      from tools.framework_detect import do_detect_framework
      from detection.app_identity import repository_app_name
      fw = do_detect_framework(window_title)
      framework = fw.get("framework", "unknown")
      app_name, exe_path = repository_app_name(fw, window_title)
    except Exception:
      pass
    repo = load_repo(app_name, exe_path)
    repo["exe_path"] = exe_path
    repo["framework"] = framework
    return app_name, repo

  def _resolve_repo_path(self, repo: dict, query: LocatorQuery) -> Optional[str]:
    if query.repo_path:
      return query.repo_path
    from detection.repo_lookup import find_best_repo_path
    return find_best_repo_path(
      repo,
      name=query.name,
      role=query.role,
      automation_id=query.automation_id,
      window_title=query.window_title,
    )

  def _ocr_finder(self, text: str, window_title: Optional[str]) -> list[dict]:
    try:
      from tools.ocr import do_find_text_dual
      result = do_find_text_dual(text, window_title=window_title)
      return [{
        "name": m["text"],
        "role": "text",
        "x": m["x"], "y": m["y"],
        "width": m["width"], "height": m["height"],
        "value": "",
        "backend": m.get("engine", "ocr"),
      } for m in result.get("matches", [])]
    except Exception:
      return []

  def _try_repo(self, repo: dict, query: LocatorQuery) -> Optional[ResolveResult]:
    path = self._resolve_repo_path(repo, query)
    if not path:
      return None
    from detection.repo_resolver import resolve_repo_object
    result = resolve_repo_object(
      repo,
      path,
      self._orch,
      window_title=query.window_title,
      template_matcher=self._template_match,
      ocr_finder=self._ocr_finder,
    )
    if not result.get("found"):
      return None
    elem = result["element"]
    obj = result.get("obj", {})
    lr = obj.get("last_resolution", {})
    return ResolveResult(
      found=True,
      layer="repository",
      backend=elem.get("backend_used", lr.get("backend", "uia")),
      method=result.get("method", "repository"),
      confidence=0.95,
      elements=[elem],
      repo_path=path,
    )

  def _template_match(self, template_rel: str, window_title: Optional[str]) -> Optional[dict]:
    try:
      import cv2
      import numpy as np
      from pathlib import Path
      from tools.screenshot import capture_screenshot
      from tools.image_utils import load_image_from_screenshot

      template_path = Path.home() / ".awdui-mcp" / "repository-assets" / template_rel
      if not template_path.exists():
        legacy = Path.home() / ".awdui-mcp" / "repositories" / template_rel
        if legacy.exists():
          template_path = legacy
      if not template_path.exists():
        assets_root = Path.home() / ".awdui-mcp" / "repository-assets"
        for p in assets_root.rglob(Path(template_rel).name):
          template_path = p
          break
      if not template_path.exists():
        return None
      shot = capture_screenshot(window_title=window_title)
      screen = load_image_from_screenshot(shot)
      screen_gray = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2GRAY)
      tmpl = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
      if tmpl is None:
        return None
      res = cv2.matchTemplate(screen_gray, tmpl, cv2.TM_CCOEFF_NORMED)
      _, max_val, _, max_loc = cv2.minMaxLoc(res)
      if max_val < 0.75:
        return None
      h, w = tmpl.shape[:2]
      x, y = max_loc
      return {
        "confidence": float(max_val),
        "element": {
          "name": "",
          "role": "template",
          "x": x, "y": y,
          "width": w, "height": h,
          "value": "",
          "backend": "template",
        },
      }
    except Exception:
      return None

  def _native_layer(self, query: LocatorQuery, options: ResolveOptions) -> Optional[ResolveResult]:
    from tools.perf import is_fast_mode
    fast = is_fast_mode()
    backends = [options.backend] if options.backend else self._orch._backend_order(query.window_title)
    all_matches: list[tuple[str, DetectedElement]] = []
    best_list: list[DetectedElement] = []
    best_backend = ""

    for bname in backends:
      b = self._orch._backends.get(bname)
      if not b or not b.is_available():
        continue
      try:
        matches = b.find_elements(
          name=query.name,
          role=query.role,
          automation_id=query.automation_id,
          class_name=query.class_name,
          window_title=query.window_title,
          index=0,
        )
        for m in matches:
          sc = score_element_match(
            m,
            name=query.name,
            role=query.role,
            automation_id=query.automation_id,
            class_name=query.class_name,
          )
          m.confidence = sc
          all_matches.append((bname, m))
        if fast and matches:
          best_list = matches
          best_backend = bname
          break
        if not fast:
          elems = b.list_elements(window_title=query.window_title, max_depth=4)
          named = [e for e in elems if e.name]
          avg_conf = sum(e.confidence for e in elems) / len(elems) if elems else 0
          if len(named) >= _MIN_NAMED_ELEMENTS and avg_conf >= _MIN_AVG_CONFIDENCE:
            if matches:
              top_sc = max(
                score_element_match(m, name=query.name, role=query.role,
                                    automation_id=query.automation_id, class_name=query.class_name)
                for m in matches
              )
              if not best_list or top_sc > 0.5:
                best_list = matches
                best_backend = bname
            if matches and query.name:
              break
          elif matches:
            best_list = matches
            best_backend = bname
      except Exception:
        continue

    if not all_matches and not best_list:
      return None

    if all_matches:
      all_matches.sort(key=lambda t: t[1].confidence, reverse=True)
      deduped = dedupe_elements([m for _, m in all_matches])
      if deduped:
        best_list = deduped
        best_backend = all_matches[0][0]

    if not best_list:
      return None

    idx = min(query.index, len(best_list) - 1) if query.index > 0 else 0
    selected = best_list if query.index == 0 and not options.strict else [best_list[idx]]
    if options.strict and len(best_list) > 1:
      return ResolveResult(found=False, error=f"strict mode: {len(best_list)} matches")

    conf = best_list[idx].confidence if best_list else 0.0
    return ResolveResult(
      found=True,
      layer="native",
      backend=best_backend,
      method=best_backend,
      confidence=conf,
      elements=[dict_to_legacy_element(e.to_dict()) for e in selected],
    )

  def _ocr_layer(self, query: LocatorQuery) -> Optional[ResolveResult]:
    if not query.name:
      return None
    try:
      from tools.ocr import do_find_text_dual
      ocr_result = do_find_text_dual(query.name, window_title=query.window_title)
      if not ocr_result.get("matches"):
        return None
      elements = [{
        "name": m["text"],
        "role": "text",
        "x": m["x"], "y": m["y"],
        "width": m["width"], "height": m["height"],
        "value": "",
        "backend": m.get("engine", "ocr"),
        "confidence": m.get("confidence", 0.8),
      } for m in ocr_result["matches"]]
      idx = min(query.index, len(elements) - 1) if query.index > 0 else 0
      return ResolveResult(
        found=True,
        layer="ocr",
        backend="ocr",
        method="ocr_dual",
        confidence=elements[idx].get("confidence", 0.8),
        elements=[elements[idx]] if query.index else elements,
      )
    except Exception:
      return None

  def _visual_layer(self, query: LocatorQuery) -> Optional[ResolveResult]:
    if not query.name:
      return None
    try:
      from tools.screenshot import capture_screenshot
      from tools.visual_detect import detect_ui_regions
      from tools.image_utils import load_image_from_screenshot, region_to_element_dict
      shot = capture_screenshot(window_title=query.window_title)
      img = load_image_from_screenshot(shot)
      regions = detect_ui_regions(img, scale=1.0)
      matches = [r for r in regions if query.name.lower() in (r.get("text") or "").lower()]
      if not matches:
        return None
      elements = [region_to_element_dict(m, backend="visual") for m in matches]
      return ResolveResult(
        found=True,
        layer="visual",
        backend="visual",
        method="visual",
        confidence=0.6,
        elements=elements,
      )
    except Exception:
      return None

  def _agentic_layer(self, query: LocatorQuery) -> ResolveResult:
    try:
      from tools.screenshot import capture_screenshot
      from tools.visual_detect import detect_ui_regions, format_regions_text
      from tools.image_utils import load_image_from_screenshot
      from tools.ocr import do_find_text_dual

      shot = capture_screenshot(window_title=query.window_title)
      img = load_image_from_screenshot(shot)
      tree = self._orch.list_elements(window_title=query.window_title, max_depth=3)
      ocr = do_find_text_dual(query.name or "", window_title=query.window_title) if query.name else {"matches": []}
      regions = detect_ui_regions(img, scale=1.0)
      ctx = {
        "screenshot_path": shot.get("path", ""),
        "element_count": tree.get("count", 0),
        "tree_sample": tree.get("elements", [])[:30],
        "ocr_matches": ocr.get("matches", [])[:20],
        "visual_regions": format_regions_text(regions[:15]),
        "query": {"name": query.name, "role": query.role, "automation_id": query.automation_id},
        "hint": "Use suggested_actions to pick the best candidate or call highlight_element to verify.",
        "suggested_actions": [],
      }
      for m in ocr.get("matches", [])[:5]:
        ctx["suggested_actions"].append({"type": "ocr", "text": m["text"], "x": m["x"], "y": m["y"]})
      for i, r in enumerate(regions[:5]):
        ctx["suggested_actions"].append({
          "type": "visual",
          "text": r.get("text", ""),
          "x": r["x"], "y": r["y"],
          "index": i,
        })
      return ResolveResult(
        found=False,
        layer="agentic",
        backend="agentic",
        method="agentic",
        agentic_context=ctx,
        error=f"'{query.name}' not found — agentic context attached for reasoning",
      )
    except Exception as exc:
      return ResolveResult(found=False, layer="agentic", error=str(exc))

  def resolve(self, query: LocatorQuery, options: Optional[ResolveOptions] = None) -> ResolveResult:
    options = options or ResolveOptions()
    trace_id = uuid.uuid4().hex[:12]
    deadline = time.monotonic() + options.timeout_ms / 1000.0
    app_name, repo = self._app_context(query.window_title)

    memory_key = make_key(
      app_name,
      query.window_title or "",
      query.repo_path or query.name or query.automation_id or "",
    )
    strat = get_strategy(memory_key)

    def _try_layers() -> ResolveResult:
      # Layer -1: repository
      r = self._try_repo(repo, query)
      if r and r.found:
        r.trace_id = trace_id
        return r

      # Layer 0: preferred backend from memory
      if strat and strat.get("preferred_backend"):
        mem_opts = ResolveOptions(
          strict=options.strict,
          backend=strat["preferred_backend"],
          remember=options.remember,
        )
        r = self._native_layer(query, mem_opts)
        if r and r.found:
          r.layer = "memory"
          r.trace_id = trace_id
          return r
        record_miss(memory_key)

      # Layer 1: native (all backends, quality gate)
      r = self._native_layer(query, options)
      if r and r.found:
        r.trace_id = trace_id
        return r

      # FlaUI explicit retry if not in order
      if "flaui" in self._orch._backends and self._orch._backends["flaui"].is_available():
        try:
          matches = self._orch._backends["flaui"].find_elements(
            name=query.name, role=query.role, window_title=query.window_title,
          )
          if matches:
            r = ResolveResult(
              found=True,
              layer="native",
              backend="flaui",
              method="flaui",
              confidence=0.85,
              elements=[dict_to_legacy_element(m.to_dict()) for m in matches],
              trace_id=trace_id,
            )
            return r
        except Exception:
          pass

      # Layer 2: OCR dual
      r = self._ocr_layer(query)
      if r and r.found:
        r.trace_id = trace_id
        return r

      # Layer 3: visual
      r = self._visual_layer(query)
      if r and r.found:
        r.trace_id = trace_id
        return r

      # Layer 4: agentic
      if options.agentic:
        return self._agentic_layer(query)

      hint = ""
      try:
        from tools.framework_detect import do_detect_framework
        fw = do_detect_framework(query.window_title)
        if fw.get("hints"):
          hint = f" [{fw['framework'].upper()}: {fw['hints'][0]}]"
      except Exception:
        pass
      return ResolveResult(
        found=False,
        trace_id=trace_id,
        error=f"'{query.name}' not found via any layer.{hint}",
      )

    result = _try_layers()

    if result.found:
      record_success(
        memory_key,
        layer=result.layer,
        backend=result.backend,
      )
      if options.remember and result.elements:
        elem = result.elements[0]
        if query.repo_path:
          swf_class = infer_swf_class(elem.get("role", ""), elem.get("class_name", ""))
          try:
            _, chain = parse_repo_path(query.repo_path)
            parent = chain[-2] if len(chain) > 1 else ""
          except ValueError:
            parent = ""
          upsert_object(
            repo,
            query.repo_path,
            obj_class=swf_class,
            parent=parent,
            element=elem,
            identification=build_identification(elem, swf_class),
            last_resolution={
              "layer": result.layer,
              "backend": result.backend,
              "bbox": {
                "x": elem.get("x", 0),
                "y": elem.get("y", 0),
                "w": elem.get("width", 0),
                "h": elem.get("height", 0),
              },
            },
          )
          result.repo_updated = True
        elif query.name or query.automation_id:
          try:
            from detection.auto_repo import maybe_remember_element, auto_repo_path
            path = maybe_remember_element(
              elem,
              window_title=query.window_title,
              repo_path=auto_repo_path(query.window_title, elem),
              backend=result.backend,
            )
            if path:
              result.repo_updated = True
          except Exception:
            pass

      if options.highlight and result.elements:
        try:
          from tools.highlight import highlight_element_dict
          highlight_element_dict(result.elements[0])
        except Exception:
          pass

    return result

  def build_detection_context(self, query: LocatorQuery) -> dict:
    result = self._agentic_layer(query)
    if result.agentic_context:
      return result.agentic_context
    if result.error:
      return {"error": result.error}
    return {}

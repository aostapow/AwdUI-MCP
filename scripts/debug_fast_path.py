import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp-servers" / "awdui-server"))

from tools.target_window import set_target
from tools.windows import do_focus_window

WINDOW = "Calculadora"
set_target(WINDOW)
do_focus_window(WINDOW, "focus")

from detection.object_repository import load_repo, get_object
from detection.orchestrator import get_orchestrator
from detection.repo_resolver import resolve_repo_object
from tools.framework_detect import do_detect_framework
from detection.app_identity import repository_app_name

fw = do_detect_framework(WINDOW)
app, exe = repository_app_name(fw, WINDOW)
repo = load_repo(app, exe)

for path in [
    "Calculadora/num1Button",
    "Calculadora/num5Button",
    "Calculadora/multiplyButton",
]:
    obj = get_object(repo, path)
    lr = obj.get("last_resolution") or {}
    print(path, "success_count=", lr.get("success_count"), "bbox=", lr.get("bbox"))
    orch = get_orchestrator()
    t0 = time.perf_counter()
    r = resolve_repo_object(repo, path, orch, window_title=WINDOW)
    ms = (time.perf_counter() - t0) * 1000
    print(f"  -> {ms:.0f}ms method={r.get('method')} found={r.get('found')}")

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp-servers" / "awdui-server"))

from tools.target_window import set_target
from tools.windows import do_focus_window

WINDOW = "Calculadora"
set_target(WINDOW)
do_focus_window(WINDOW, "focus")

from detection.repo_lookup import find_best_repo_path, resolve_via_repository
from detection.orchestrator import get_orchestrator
from tools.framework_detect import do_detect_framework
from detection.app_identity import repository_app_name
from detection.object_repository import load_repo

orch = get_orchestrator()
fw = do_detect_framework(WINDOW)
app, exe = repository_app_name(fw, WINDOW)
repo = load_repo(app, exe)
print("app", app, "exe", exe)

queries = [
    {"name": "1"},
    {"name": "5"},
    {"automation_id": "num1Button"},
    {"automation_id": "multiplyButton"},
]
for kw in queries:
    kw["window_title"] = WINDOW
    t0 = time.perf_counter()
    path = find_best_repo_path(repo, **{k: v for k, v in kw.items() if k != "window_title"}, window_title=WINDOW)
    t1 = time.perf_counter()
    print(f"find_best {kw} -> {path} ({(t1 - t0) * 1000:.0f}ms)")
    t0 = time.perf_counter()
    r = resolve_via_repository(orch, **kw)
    t1 = time.perf_counter()
    if r:
        print(
            f"  resolve found={r.get('found')} layer={r.get('layer')} "
            f"method={r.get('method')} path={r.get('repo_path')} ({(t1 - t0) * 1000:.0f}ms)"
        )
    else:
        print(f"  resolve -> None ({(t1 - t0) * 1000:.0f}ms)")

"""Prueba visible de screenshot post-cambio (mismo código que el MCP)."""
import base64
import io
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "awdui-server")
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from PIL import Image

from screenshot_manager import ScreenshotManager
from awdui_platform.win32_backend import is_window_in_foreground
import tools.screenshot as screenshot_mod
from tools.screenshot import (
    _capture_quality,
    _is_uwp_splash_image,
    capture_screenshot,
)
from tools.windows import do_focus_window, do_list_windows, find_matching_window

OUT = os.path.join(os.environ.get("TEMP", "."), "awdui_diag")
os.makedirs(OUT, exist_ok=True)


def main() -> int:
    print("=== PRUEBA EN VIVO POST-CAMBIO ===")

    match = find_matching_window("Calculadora", do_list_windows())
    win = match.get("window")
    if not win:
        print("ERROR: no hay ventana Calculadora abierta. Abrila y volvé a correr.")
        return 1

    hwnd = int(win["hwnd"])
    print(
        f"ventana: hwnd={hwnd} proc={win.get('process_name')} "
        f"rect=({win['x']},{win['y']}) {win['width']}x{win['height']}"
    )

    fr = do_focus_window("Calculadora", "focus")
    print(f"focus_window: success={fr.get('success')} window={fr.get('window')}")
    print(f"foreground_match={is_window_in_foreground(hwnd, 'Calculadora')}")

    screenshot_mod.screenshot_manager = ScreenshotManager(OUT)
    result = capture_screenshot(window_title="Calculadora")
    raw = base64.b64decode(result["image"])
    img = Image.open(io.BytesIO(raw))

    copy_path = os.path.join(OUT, "prueba_post_cambio.jpg")
    img.save(copy_path, "JPEG")

    quality = _capture_quality(img)
    splash = _is_uwp_splash_image(img)
    ok = quality >= 80 and not splash

    print(
        f"screenshot: {result['original_width']}x{result['original_height']} "
        f"quality={quality:.1f} splash={splash}"
    )
    print(f"archivo MCP: {result['path']}")
    print(f"copia visible: {copy_path}")
    print("RESULTADO:", "OK" if ok else "FALLO")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())

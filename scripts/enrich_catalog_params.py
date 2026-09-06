"""Enrich MCP_TOOLS_REFERENCE.md parameter docs from code audit."""
from __future__ import annotations

import re
from pathlib import Path

REFERENCE = Path(__file__).resolve().parents[1] / "docs" / "MCP_TOOLS_REFERENCE.md"

PARAMS: dict[str, str] = {
    "list_windows": "`app_id` (opcional — filtra ventanas del proceso de esa sesión).",
    "find_element": "`automation_id` (exacto), `name` (parcial), `role`, `class_name`, `index`, `window_title`/`title`, `window_handle`, `tree_mode`, `include_offscreen`.",
    "find_all_elements": "`automation_id`, `name`, `role`, `window_title`/`title`, `window_handle`, `app_id`.",
    "find_elements": "`control_type`, `id_contains`, `name_contains`, `max_results` (50), `window_title`/`title`, `window_handle`, `app_id`.",
    "find_elements_fuzzy": "`query` (req), `control_type`, `min_score` (0.55), `max_results` (20), `window_title`/`title`, `window_handle`, `app_id`.",
    "get_snapshot": "`max_depth` (3), `role`, `window_title`/`title`, `window_handle`, `app_id`.",
    "get_tree_hash": "`max_depth` (6), `window_title`/`title`, `window_handle`, `app_id`.",
    "get_element_bounds": "`automation_id`, `name`, `role`, `index` (0; `-1` = primero), `fuzzy_match`, `window_title`/`title`, `window_handle`, `app_id`.",
    "read_element": "`automation_id`, `name`, `role`, `window_title`/`title`, `window_handle`, `index` (0), `app_id`.",
    "read_element_by_index": "`index` (req), `automation_id`, `name`, `role`, `window_title`/`title`, `window_handle`, `app_id`.",
    "wait_for_element": "`automation_id`, `name`, `role`, `window_title`/`title`, `window_handle`, `app_id`, `timeout_ms` (10000), `poll_ms` (100).",
    "wait_for_condition": "`property`, `expected_value` (req), `automation_id`, `name`, `role`, `window_title`/`title`, `window_handle`, `app_id`, `timeout_ms`, `poll_ms`.",
    "wait_for_input_idle": "`window_title`/`title`, `app_id`, `timeout_ms` (10000).",
    "element_exists": "`automation_id`, `name`, `role`, `window_title`/`title`, `window_handle`, `app_id`.",
    "check_session_status": "`window_title`/`title`, `app_id`.",
    "invalidate_cache": "`window_title`/`title`, `hwnd`, `app_id`.",
    "type_into_element": "`text` (req), `automation_id`, `name`, `clear_first` (true), `window_title`/`title`, `app_id`.",
    "set_value_hwnd": "`window_handle` (req), `value` (req), `automation_id`, `name`, `fuzzy_match`, `index` (0).",
    "click_element": "`automation_id`, `name`, `role`, `window_title`/`title`, `index`, `window_handle`, `app_id`, `fuzzy_match`, `capture`, `capture_full`, `verify_automation_id`, `verify_name_contains`, `verify_timeout_ms` (5000), `verify_poll_ms` (100).",
    "scroll_element": "`automation_id` o `name`+`role`, `index` (-1 = primero), `direction` (up/down/left/right), `amount` (large/small), `repeat`, `clicks`, `horizontal_percent`/`vertical_percent`, `window_title`/`title`, `window_handle`, `app_id`.",
    "scroll_into_view": "`automation_id` (req), `name`, `role`, `index`, `window_title`/`title`, `window_handle`, `app_id`.",
    "realize_virtualized_item": "`automation_id` (req), `name`, `role`, `index`, `window_title`/`title`, `window_handle`, `app_id`.",
    "double_click_element": "`automation_id`, `name`, `role`, `index`, `fuzzy_match`, `window_title`/`title`, `window_handle`, `app_id`, `capture`, `capture_full`.",
    "right_click_element": "`automation_id`, `name`, `role`, `index`, `fuzzy_match`, `window_title`/`title`, `window_handle`, `app_id`, `capture`, `capture_full`.",
    "drag_element": "`source_automation_id`, `source_name`, `source_control_type`, `source_index` (-1), `target_automation_id`, `target_name`, `target_control_type`, `target_index` (-1), `window_title`/`title`, `window_handle`, `app_id`, `duration` (0.5), `capture`, `capture_full`.",
    "expand_collapse_element": "`action` (expand|collapse|toggle), `automation_id`, `name`, `window_title`/`title`, `app_id`.",
    "select_option": "`option_text` (req), `automation_id`, `name`, `index` (-1 = primero), `window_title`/`title`, `app_id`.",
    "click_element_hwnd": "`window_handle` (req), `automation_id`, `name`, `control_type`, `fuzzy_match`, `index` (0), `capture`, `capture_full`.",
    "take_screenshot_optimized": "`max_tokens` (8000), `window_title`/`title`, `app_id`.",
    "annotate_screenshot": "`automation_ids` (list), `names` (list), `window_title`/`title`, `app_id`, `output_path`.",
    "fill_form": "`fields_json` / `fields` (req), `window_title`/`title`, `window_handle` (modal hijo).",
    "get_all_values": "`window_title`/`title`, `window_handle`, `max_depth` (12).",
    "set_element_value": "`value` (req), `automation_id`, `name`, `window_title`/`title`, `index`, `window_handle`.",
}


def set_field(text: str, tool: str, field: str, value: str) -> str:
    marker = f"### `{tool}`"
    idx = text.find(marker)
    if idx == -1:
        raise KeyError(f"Tool section not found: {tool}")
    rest = text[idx:]
    needle = f"**{field}:**"
    fidx = rest.find(needle)
    if fidx == -1:
        raise KeyError(f"Field {field} not found in {tool}")
    start = fidx + len(needle)
    end = rest.find("\n", start)
    if end == -1:
        end = len(rest)
    return text[:idx] + rest[:start] + " " + value + rest[end:]


def main() -> None:
    text = REFERENCE.read_text(encoding="utf-8")

    for tool, params in PARAMS.items():
        text = set_field(text, tool, "Parámetros clave", params)

    text = set_field(
        text,
        "list_apps",
        "Evitar",
        "Dejar sesiones `app_id` abiertas al terminar — usar `close_app` o `release_all`.",
    )

    text = set_field(
        text,
        "launch_app",
        "Qué hace",
        "Lanza un ejecutable; por defecto reutiliza instancia existente (enfoca y cierra duplicados). "
        "En la respuesta incluye `app_id` cuando se registra sesión (igual que `attach_to_*`).",
    )
    text = set_field(
        text,
        "launch_app",
        "Relacionadas",
        "`wait_for_input_idle`, `invalidate_cache`, `set_target_window`, `list_apps`, `attach_to_app`",
    )

    conv_old = "| `role` | Tipo UIA: `Button`, `Edit`, `ComboBox`, `Table`, etc. |\n\n**Orden"
    conv_new = (
        "| `role` | Tipo UIA: `Button`, `Edit`, `ComboBox`, `Table`, etc. |\n"
        "| `app_id` | Sesión multi-app de `launch_app` / `attach_to_*`. Scope alternativo a `set_target_window`. |\n"
        "| `index` | Match a usar (0 = primero). `-1` = primer match (convención legacy). |\n"
        "| `fuzzy_match` | Búsqueda tolerante a typos en `name`/`automation_id`. |\n\n"
        "**Orden"
    )
    if conv_old in text:
        text = text.replace(conv_old, conv_new, 1)

    changelog = "| 2026-09-06 | Auditoría parámetros: `app_id`, scope HWND, `fuzzy_match`, `index=-1` y firmas reales en 30+ tools. |\n"
    if "Auditoría parámetros" not in text:
        text = text.replace(
            "| 2026-09-06 | Catálogo: tools de la antigua §17",
            changelog + "| 2026-09-06 | Catálogo: tools de la antigua §17",
            1,
        )

    REFERENCE.write_text(text, encoding="utf-8")
    print(f"enrich_catalog: updated {len(PARAMS)} tool param sections")


if __name__ == "__main__":
    main()

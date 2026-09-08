"""One-off generator for Teams harness flow files."""
from __future__ import annotations

from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / ".cursor" / "skills" / "teams" / "flows"

FLOWS: dict[str, str] = {
    "TE-00-hooks-session.md": """# TE-00 — Hooks + sesión MCP

**Estado:** pending | **Recovery:** L0

## Objetivo
Validar MCP vivo antes de tocar Teams.

## Pasos

### Paso 1 — check_version
| | |
|---|---|
| **Act** | `check_version` |
| **Esperado** | v0.4.0 up to date |

### Paso 2 — check_session_status
| | |
|---|---|
| **Act** | `check_session_status` |
| **Verify** | uia_find=true |

### Paso 3 — state.json
| | |
|---|---|
| **Verify** | teams_perfect=false; teams_matrix 21 flujos |

## Criterio met
MCP vivo + state harness Teams presente.
""",
    "TE-01-launch.md": """# TE-01 — Launch Teams limpio

**Estado:** pending | **Recovery:** L3

## Pasos
1. `launch_app(path="ms-teams:", replace=true)` — fallback Teams.exe
2. `wait_for_input_idle` ≤15s
3. `set_target_window("Teams", focus_policy="minimal")`
4. `detect_framework` → electron
5. `screenshot(scope=window)`

## Criterio met
Una instancia; target fijado; framework electron.
""",
    "TE-02-discovery.md": """# TE-02 — Discovery + mapa UIA

**Estado:** pending

## Pasos
1. `observe_ui_tool` + `ui_fingerprint`
2. `list_elements(max_depth=8)` — timing
3. `spy_tree(max_depth=6)` + `ascii_ui_view`
4. `list_elements` role=Button/Edit/ListItem
5. `discover_control_interaction` compose box
6. Actualizar [element-map.md](../element-map.md)
7. `screenshot(scope=window)`

## Criterio met
element-map con nav + search + compose documentados.
""",
    "TE-03-nav-rail.md": """# TE-03 — Nav rail

**Estado:** pending

Navegar Chat → Equipos → Calendario → Llamadas → volver Chat.
Verify panel cambia (`list_elements` / screenshot sub-paso Chat).
**No** iniciar llamada.
""",
    "TE-04-search-awamori.md": """# TE-04 — Buscar Nicolás Awamori

**Estado:** pending

1. Ctrl+E o click Buscar
2. `type_text("Nicolas Awamori")`
3. Verify resultados contienen Awamori
4. Screenshot — **no** abrir chat aún
""",
    "TE-05-chat-readonly.md": """# TE-05 — Chat 1:1 Awamori (lectura)

**Estado:** pending

1. Abrir resultado Awamori
2. Verify header = Nicolás Awamori
3. `discover_control_interaction` compose — **no** escribir
4. Screenshot
""",
    "TE-06-compose-no-send.md": """# TE-06 — Compose sin enviar

**Estado:** pending

1. Escribir `[AwdUI-MCP-TE] borrador TE-06 — no enviar`
2. Verify solo en compose — **no** Enter
3. Limpiar compose (Ctrl+A Delete)
""",
    "TE-07-send-awamori.md": """# TE-07 — Enviar a Nicolás Awamori

**Estado:** pending | **ÚNICO envío permitido**

Ver [message-safety.md](../protocol/message-safety.md).

1. Verify header Awamori — STOP si otro
2. Mensaje: `[AwdUI-MCP-TE] harness TE-07 verificación agentica — OK si recibís esto en prueba MCP.`
3. Enviar (botón o Enter)
4. Verify burbuja en historial (o reuse <24h)
5. Screenshot
""",
    "TE-08-scroll-history.md": """# TE-08 — Scroll historial

Scroll arriba/abajo en lista mensajes; verify sin perder scope.
""",
    "TE-09-teams-channels.md": """# TE-09 — Equipos/canales lectura

Abrir equipo + canal; **prohibido** publicar; volver Chat.
""",
    "TE-10-calendar.md": """# TE-10 — Calendario

Rail Calendario; list_elements; screenshot; volver Chat.
""",
    "TE-11-calls-ui.md": """# TE-11 — Llamadas UI

Rail Llamadas; abrir nueva llamada → Cancel; **no** marcar.
""",
    "TE-12-settings.md": """# TE-12 — Configuración

Menú perfil; 1 sección; cerrar; screenshot.
""",
    "TE-13-activity.md": """# TE-13 — Actividad

Feed actividad; abrir item; cerrar.
""",
    "TE-14-new-chat-cancel.md": """# TE-14 — Nuevo chat cancel

Nuevo chat → Cancel antes de otro destinatario.
""",
    "TE-15-attach-cancel.md": """# TE-15 — Adjuntar cancel

Clip → picker → Cancel → verify picker cerrado.
""",
    "TE-16-emoji-dismiss.md": """# TE-16 — Emoji dismiss

Abrir emoji panel → Escape.
""",
    "TE-17-keyboard-shortcuts.md": """# TE-17 — Atajos

Ctrl+E abre búsqueda; Escape cierra.
""",
    "TE-18-stale-recovery.md": """# TE-18 — Recovery stale

L3 relaunch + TE-01 + re-abrir chat Awamori.
""",
    "TE-19-session-health.md": """# TE-19 — Session health

check_session_status; get_tree_hash; detection_health.
""",
    "TE-20-session-close.md": """# TE-20 — Cierre sesión

screenshot; set_target_window(""); actualizar teams_matrix_progress.
""",
}


def main() -> None:
    BASE.mkdir(parents=True, exist_ok=True)
    for name, body in FLOWS.items():
        (BASE / name).write_text(body.strip() + "\n", encoding="utf-8")
    print(f"Wrote {len(FLOWS)} files to {BASE}")


if __name__ == "__main__":
    main()

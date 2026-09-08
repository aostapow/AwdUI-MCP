# launch_app: protocolos URI y resolución WindowsApps (Store)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-06 20:28:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | `tools/windows.py`, `tools/app_launch.py` |
| **Tool afectada** | launch_app |
| **Tipo de gap** | tool_gap |
| **Nivel** | L4 |
| **MCP versión** | v0.4.0 |

## Resumen

**Problema:** `launch_app(path="ms-teams:")` y `launch_app(path="Teams.exe")` fallan con
`WinError 2` (archivo no encontrado) porque `subprocess.Popen([path])` no resuelve
protocolos shell ni ejecutables empaquetados en `%LOCALAPPDATA%\Microsoft\WindowsApps\`.
Solo funciona con ruta absoluta al `.exe` de WindowsApps.

**Solución:** (1) Detectar URIs con `:` (`ms-teams:`, `calculator:`, `shell:AppsFolder\…`)
y lanzar vía `os.startfile(path)` o `subprocess.run(["cmd", "/c", "start", "", path], shell=False)`.
(2) Resolver alias conocidos (`Teams.exe`, `ms-teams`) buscando en WindowsApps y
`Get-StartApps` / registro App Paths antes de Popen. (3) Respuesta incluir
`resolved_path`, `launch_method` (`popen` | `protocol` | `windowsapps`). (4) Documentar
en `MCP_TOOLS_REFERENCE.md` y skill `teams/flows/TE-01-launch.md`.

**Dónde:** `do_launch_app`, nuevo helper `resolve_launch_target(path)` en `app_launch.py`;
tests `tests/test_launch_app_protocol.py`.

## Contexto del turno

Harness Teams TE-01 (MCP v0.4.0):

| Intento | Resultado |
|---------|-----------|
| `launch_app(ms-teams:)` | FAIL WinError 2 |
| `launch_app(Teams.exe)` | FAIL WinError 2 |
| Ruta completa WindowsApps `ms-teams.exe` | OK PID 30540 |

Tras launch manual: `set_target_window` exact title, `detect_framework` unknown,
navegación TE-03 OK con `invoke_element` nav rail.

Skills: `awdui-mcp-objective`, `teams/SKILL.md`, `teams-mcp-harness/SKILL.md`.

## Cambio propuesto (pseudodiff)

```python
# app_launch.py
def resolve_launch_target(path: str) -> tuple[str, str]:
    """Return (executable_or_uri, method)."""
    if ":" in path and not re.match(r"^[A-Za-z]:\\", path):
        return path, "protocol"
    if not os.path.isabs(path) and not os.path.exists(path):
        resolved = _find_in_windowsapps(path) or _find_app_paths(path)
        if resolved:
            return resolved, "windowsapps"
    return path, "popen"

# windows.py do_launch_app
target, method = resolve_launch_target(path)
if method == "protocol":
    os.startfile(target)  # or subprocess start
elif method == "windowsapps":
    proc = subprocess.Popen([target] + args)
else:
    proc = subprocess.Popen([target] + args)
return {..., "launch_method": method, "resolved_path": target}
```

## Test de abstracción (L4)

Aplica a cualquier app Store/UWP con protocol handler (Teams, Calculadora `calculator:`,
OneNote `onenote:`) — no específico de Teams.

## Verificación de duplicados

- Sin propuesta abierta previa para protocol/WindowsApps en `launch_app`.
- Distinto de `stale-element-cache` (post-launch cache) y `try_reuse_existing` (reuse PID).

## Esfuerzo observado

TE-01 bloqueado hasta que el agente descubrió ruta WindowsApps manualmente; 2 intentos
fallidos + lectura de skill gaps.

## Criterio de aceptación

- [ ] `launch_app("ms-teams:")` inicia Teams en entorno con app instalada (mock en CI).
- [ ] `launch_app("Teams.exe")` resuelve vía WindowsApps sin ruta absoluta.
- [ ] Respuesta JSON incluye `launch_method` y `resolved_path`.
- [ ] `docs/MCP_TOOLS_REFERENCE.md` § `launch_app` actualizado.
- [ ] `tests/test_launch_app_protocol.py` pasa en pytest.

## Beneficios futuros

- TE-01 y harness de apps Store sin hardcodear rutas por usuario.
- Menos fricción al reutilizar `launch_app` genérico en skills de producto.

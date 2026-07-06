# Guía para agentes de IA — instalación y actualización del MCP AwdUI

Checklist ejecutable para instalar, migrar o reparar AwdUI sin intervención humana innecesaria.

## Reglas críticas

1. **Entry point MCP:** siempre `scripts/launcher.py` (ruta absoluta o `${CLAUDE_PLUGIN_ROOT}/scripts/launcher.py`). **Nunca** `server.py` directo — sin launcher no hay auto-update ni carga de `.env`.
2. **Dependencias:** el servidor crea `~/.awdui-mcp/.venv` en el primer arranque; tras un update zip se ejecuta `pip install -r requirements.txt` en ese venv.
3. **stdout reservado:** el protocolo MCP usa stdout; logs van a stderr.
4. **No commitear** `.env` ni tokens.
5. **Reiniciar el cliente MCP** después de cambiar `mcp.json` o aplicar un update en disco.

## Instalación nueva (desde zip)

| # | Acción | Detalle |
|---|--------|---------|
| 1 | Descargar último release | `AwdUI-MCP-vX.Y.Z.zip` desde [releases](https://github.com/aostapow/AwdUI-MCP/releases/latest) |
| 2 | Extraer | Fuera de OneDrive/Dropbox. Ej: `%LOCALAPPDATA%\awdui-mcp\` |
| 3 | Configurar | Copiar `.env.example` → `.env` si hace falta |
| 4 | Probar arranque | `python scripts/launcher.py` — stderr debe mostrar inicio del servidor |
| 5 | Registrar MCP | Editar configuración del cliente (Cursor / Claude Code) |
| 6 | Verificar | Tras reiniciar: tool `get_server_info` |

### Snippet MCP (cliente)

```json
{
  "mcpServers": {
    "awdui-mcp": {
      "command": "python",
      "args": ["C:\\ruta\\absoluta\\AwdUI-MCP\\scripts\\launcher.py"],
      "env": {}
    }
  }
}
```

### Plugin Claude Code (ya configurado)

```json
{
  "command": "python",
  "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/launcher.py"]
}
```

## Migración (instalación sin launcher)

| # | Acción |
|---|--------|
| 1 | Cambiar `args` al path de `scripts/launcher.py` |
| 2 | Confirmar `AWDUI_AUTO_UPDATE=true` en `.env` (default) |
| 3 | Reiniciar cliente MCP |
| 4 | `get_server_info` debe mostrar `launcherEntryPoint: scripts/launcher.py` |

## Actualización

| Modo | Cuándo | Cómo |
|------|--------|------|
| Automática | Default con launcher | Al iniciar: descarga zip, merge, `pip install`, arranca |
| Manual | Red restringida o preferencia | `python scripts/update.py` o `scripts\update.ps1`, reiniciar cliente |
| Desactivada | Preferencia local | `AWDUI_AUTO_UPDATE=false` en `.env` |

Cache: `%LOCALAPPDATA%\awdui-mcp\` (`last-applied.json`, `version_check.json`)

## Verificación de éxito

- `python scripts/launcher.py` → servidor en ejecución (stderr)
- Tool `get_server_info` → `mcpServerVersion`, `autoUpdateEnabled`, `lastAppliedVersion`

## Errores frecuentes

| Síntoma | Causa probable | Fix |
|---------|----------------|-----|
| JSON-RPC corrupto | Salida en stdout | Usar launcher; no prints en stdout |
| Update no aplica | Sin launcher o auto-update off | `launcher.py` + `AWDUI_AUTO_UPDATE=true` |
| No zip en release | Release sin asset | Tag debe disparar CI o adjuntar `AwdUI-vX.Y.Z.zip` |
| Update falla red | Sin GitHub API | Manual zip o `AWDUI_UPDATE_URL` mirror |

## Versión mínima en flujos del agente

1. Invocar `get_server_info` al inicio del flujo.
2. Comparar `mcpServerVersion` con el umbral documentado.
3. Si es inferior: `python scripts/update.py` y reiniciar cliente.

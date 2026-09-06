# Cursor sessionStart hook — inyecta objetivo MCP si el ciclo está activo.
$ErrorActionPreference = "Stop"
$root = if ($env:CURSOR_PROJECT_DIR) { $env:CURSOR_PROJECT_DIR } else { (Get-Location).Path }
$py = Join-Path $env:USERPROFILE ".awdui-mcp\.venv\Scripts\python.exe"
$script = Join-Path $root ".cursor\hooks\check_mcp_objective.py"
if (-not (Test-Path $script)) { exit 0 }
if (-not (Test-Path $py)) { $py = "python" }
Push-Location $root
try {
    & $py $script --mode session
} finally {
    Pop-Location
}
exit 0

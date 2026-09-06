# Resume MCP objective auto-continue after pause-mcp-cycle.ps1
$ErrorActionPreference = "Stop"
$root = if ($env:CURSOR_PROJECT_DIR) { $env:CURSOR_PROJECT_DIR } else { (Get-Location).Path }
$statePath = Join-Path $root ".cursor\mcp-improvement-cycle\state.json"
$pausedPath = Join-Path $root ".cursor\mcp-improvement-cycle\PAUSED"

if (Test-Path $pausedPath) {
    Remove-Item $pausedPath -Force
}

if (Test-Path $statePath) {
    $state = Get-Content $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($state.cycle_control) {
        $state.cycle_control.paused = $false
        $state.cycle_control.resumed_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    }
    if ($state.status -eq "paused") {
        $state.status = "in_progress"
    }
    $state | ConvertTo-Json -Depth 20 | Set-Content $statePath -Encoding UTF8
}

Write-Host "MCP cycle RESUMED. Stop hook will inject followup when objective_met is false."

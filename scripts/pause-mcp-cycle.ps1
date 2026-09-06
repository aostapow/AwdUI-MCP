# Pause MCP objective auto-continue (stop hook + sessionStart injection).
# Use when you stop the agent/subagent and do NOT want automatic restart.
param(
    [string]$Reason = "paused by user"
)
$ErrorActionPreference = "Stop"
$root = if ($env:CURSOR_PROJECT_DIR) { $env:CURSOR_PROJECT_DIR } else { (Get-Location).Path }
$statePath = Join-Path $root ".cursor\mcp-improvement-cycle\state.json"
$pausedPath = Join-Path $root ".cursor\mcp-improvement-cycle\PAUSED"
$ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

New-Item -ItemType File -Path $pausedPath -Force | Out-Null

if (Test-Path $statePath) {
    $state = Get-Content $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $state.cycle_control) {
        $state | Add-Member -NotePropertyName cycle_control -NotePropertyValue ([pscustomobject]@{})
    }
    $state.cycle_control.paused = $true
    $state.cycle_control | Add-Member -NotePropertyName paused_at -NotePropertyValue $ts -Force
    $state.cycle_control | Add-Member -NotePropertyName paused_reason -NotePropertyValue $Reason -Force
    $state.cycle_control | Add-Member -NotePropertyName paused_by -NotePropertyValue "user" -Force
    $state.status = "paused"
    $state | ConvertTo-Json -Depth 20 | Set-Content $statePath -Encoding UTF8
}

Write-Host "MCP cycle PAUSED. Stop hook will not inject followup."
Write-Host "Resume: scripts/resume-mcp-cycle.ps1"

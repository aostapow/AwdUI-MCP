# Pause MCP objective auto-continue (stop hook + sessionStart injection).
# Use when you stop the agent/subagent and do NOT want automatic restart.
param(
    [string]$Reason = "paused by user"
)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$pausedPath = Join-Path $root ".cursor\mcp-improvement-cycle\PAUSED"
$py = Join-Path $env:USERPROFILE ".awdui-mcp\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

New-Item -ItemType File -Path $pausedPath -Force | Out-Null

$env:AWDUI_PAUSE_REASON = $Reason
Push-Location $root
try {
    & $py -c @"
import json
import os
from datetime import datetime, timezone
from pathlib import Path
reason = os.environ.get('AWDUI_PAUSE_REASON', 'paused by user')
p = Path('.cursor/mcp-improvement-cycle/state.json')
if not p.is_file():
    raise SystemExit(0)
s = json.loads(p.read_text(encoding='utf-8-sig'))
ctrl = s.setdefault('cycle_control', {})
ctrl['paused'] = True
ctrl['paused_at'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
ctrl['paused_reason'] = reason
ctrl['paused_by'] = 'user'
s['status'] = 'paused'
p.write_text(json.dumps(s, indent=2, ensure_ascii=False) + '\n', encoding='utf-8-sig')
"@
} finally {
    Pop-Location
}

Write-Host "MCP cycle PAUSED. Stop hook will not inject followup."
Write-Host "Resume: scripts/resume-mcp-cycle.ps1"

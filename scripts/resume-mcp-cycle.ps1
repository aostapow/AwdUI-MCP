# Resume MCP objective auto-continue after pause-mcp-cycle.ps1
$ErrorActionPreference = "Stop"
$root = if ($env:CURSOR_PROJECT_DIR) { $env:CURSOR_PROJECT_DIR } else { (Get-Location).Path }
$pausedPath = Join-Path $root ".cursor\mcp-improvement-cycle\PAUSED"
$py = Join-Path $env:USERPROFILE ".awdui-mcp\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

if (Test-Path $pausedPath) {
    Remove-Item $pausedPath -Force
}

Push-Location $root
try {
    & $py -c @"
import json
from datetime import datetime, timezone
from pathlib import Path
p = Path('.cursor/mcp-improvement-cycle/state.json')
if not p.is_file():
    raise SystemExit(0)
s = json.loads(p.read_text(encoding='utf-8'))
ctrl = s.setdefault('cycle_control', {})
ctrl['paused'] = False
ctrl['resumed_at'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
if s.get('status') == 'paused':
    s['status'] = 'running'
p.write_text(json.dumps(s, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
"@
} finally {
    Pop-Location
}

Write-Host "MCP cycle RESUMED. Stop hook will inject followup when objective_met is false."

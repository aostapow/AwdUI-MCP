# Restart the AwdUI MCP server in Cursor (Windows).
# Default: bump AWDUI_RESTART in ~/.cursor/mcp.json — Cursor reloads awdui on config_changed.
# Avoid killing live processes; that races with Cursor's reconnect and causes "Connection closed".
param(
    [switch]$KillOrphans,
    [switch]$ReloadWindow
)

$ErrorActionPreference = "Stop"
$mcpPath = Join-Path $env:USERPROFILE ".cursor\mcp.json"
$serverKey = "awdui"

if (-not (Test-Path $mcpPath)) {
    Write-Error "MCP config not found: $mcpPath"
}

# 1) Bump restart nonce (regex edit — preserves JSON layout, no BOM)
$raw = [System.IO.File]::ReadAllText($mcpPath)
if ($raw.Length -ge 3 -and $raw[0] -eq [char]0xFEFF) {
    $raw = $raw.Substring(1)
}
$nonce = [string][DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
if ($raw -match '"AWDUI_RESTART"\s*:\s*"[^"]*"') {
    $raw = [regex]::Replace($raw, '"AWDUI_RESTART"\s*:\s*"[^"]*"', "`"AWDUI_RESTART`": `"$nonce`"")
} elseif ($raw -match '("awdui"\s*:\s*\{[\s\S]*?"env"\s*:\s*\{)') {
    $raw = [regex]::Replace(
        $raw,
        '("awdui"\s*:\s*\{[\s\S]*?"env"\s*:\s*\{)',
        "`${1}`n        `"AWDUI_RESTART`": `"$nonce`","
    )
} else {
    Write-Error "Could not find awdui.env block in $mcpPath"
}
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($mcpPath, $raw, $utf8NoBom)
Write-Host "[awdui] Bumped AWDUI_RESTART=$nonce (Cursor should reload awdui)"

# 2) Optional: kill only explicit orphan patterns (off by default)
if ($KillOrphans) {
    $patterns = @(
        "*AwdUI-MCP\scripts\launcher.py*",
        "*awdui-server\server.py*"
    )
    $killed = 0
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $cmd = $_.CommandLine
            if (-not $cmd) { return $false }
            foreach ($pat in $patterns) {
                if ($cmd -like $pat) { return $true }
            }
            return $false
        } |
        ForEach-Object {
            Write-Host "[awdui] Stopping orphan PID $($_.ProcessId)"
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
            $killed++
        }
    Write-Host "[awdui] Stopped $killed orphan process(es)"
}

# 3) Last resort only — reload entire Cursor window (disruptive)
if ($ReloadWindow) {
    Write-Warning "[awdui] -ReloadWindow is disruptive; prefer config bump only."
    $cursor = Join-Path $env:LOCALAPPDATA "Programs\cursor\resources\app\bin\cursor.cmd"
    if (Test-Path $cursor) {
        Start-Process -FilePath $cursor -ArgumentList @("--reuse-window", $PWD.Path) -WindowStyle Hidden
    }
}

Write-Host "[awdui] Done. If status stays Error, toggle awdui off/on in Cursor Settings > MCP."

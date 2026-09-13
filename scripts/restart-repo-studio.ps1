# Restart Repo Studio API (kills stale listener on 8765, rebuilds SPA if needed).
param(
    [int]$ApiPort = 8765,
    [switch]$Dev
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent

$conn = Get-NetTCPConnection -LocalPort $ApiPort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($conn) {
    Write-Host "[repo-studio] Stopping PID $($conn.OwningProcess) on port $ApiPort"
    Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

if ($Dev) {
    & (Join-Path $Root "scripts\start-repo-studio.ps1") -Dev -ApiPort $ApiPort
} else {
    & (Join-Path $Root "scripts\start-repo-studio.ps1") -ApiPort $ApiPort
}

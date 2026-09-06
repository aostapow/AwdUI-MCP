# Stop orphan AwdUI GUI automation sessions (mouse/keyboard hijack).
param(
    [switch]$KillPythonHarness
)

$lock = Join-Path $env:USERPROFILE ".awdui-mcp\gui_session.lock"
if (Test-Path $lock) {
    $info = Get-Content $lock -Raw | ConvertFrom-Json
    Write-Host "Found GUI session lock: pid=$($info.pid) name=$($info.name)"
    if ($info.pid) {
        $proc = Get-Process -Id $info.pid -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "Stopping pid $($info.pid) ($($proc.Path))"
            Stop-Process -Id $info.pid -Force -ErrorAction SilentlyContinue
        }
    }
    Remove-Item $lock -Force
    Write-Host "Lock removed."
} else {
    Write-Host "No gui_session.lock found."
}

if ($KillPythonHarness) {
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.CommandLine -match 'explore_calculator|calculator_orchestrator|smoke_calculator' } |
        ForEach-Object {
            Write-Host "Killing pid $($_.ProcessId): $($_.CommandLine)"
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
}

Write-Host "Done. Move mouse to corner if pyautogui failsafe needed."

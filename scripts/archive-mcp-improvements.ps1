param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$repo = Split-Path $PSScriptRoot -Parent
$py = Join-Path $env:USERPROFILE ".awdui-mcp\.venv\Scripts\python.exe"
$script = Join-Path $repo "scripts\archive_mcp_improvements.py"
$args = @($script)
if ($DryRun) { $args += "--dry-run" }
& $py @args

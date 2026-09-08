# CI smoke — fast MCP regression subset (local or pipeline)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $env:USERPROFILE ".awdui-mcp\.venv\Scripts\python.exe"

Push-Location $root
try {
    & $py -m pytest tests/test_validate_perfect_gate.py tests/test_hint_consume.py tests/test_uia_find_performance.py tests/test_find_element_target_scope.py tests/test_act_on_control.py tests/test_ancestor_scope.py tests/test_uia_pattern_tools.py tests/test_cen_grid.py -q --tb=short
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $py scripts/validate_tools_reference.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "CI smoke: OK"
}
finally {
    Pop-Location
}

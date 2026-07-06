# Create or repair ~/.awdui-mcp/.venv for the AwdUI MCP server.
$ErrorActionPreference = "Stop"

$DataDir = Join-Path $env:USERPROFILE ".awdui-mcp"
$VenvDir = Join-Path $DataDir ".venv"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Req = Join-Path $RepoRoot "mcp-servers\awdui-server\requirements.txt"

$pyExe = $env:AWDUI_PYTHON
if (-not $pyExe) {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        (Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
    ) | Where-Object { $_ -and (Test-Path $_) }
    $pyExe = $candidates | Select-Object -First 1
}
if (-not $pyExe) {
    Write-Error "Python not found. Set AWDUI_PYTHON or install Python 3.11+."
}

New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
if (Test-Path $VenvDir) {
    Write-Host "[awdui] Removing old venv: $VenvDir"
    Remove-Item -Recurse -Force $VenvDir
}

Write-Host "[awdui] Creating venv at $VenvDir (python: $pyExe)"
& $pyExe -m venv $VenvDir
$pip = Join-Path $VenvDir "Scripts\pip.exe"
& $pyExe -m pip install -U pip wheel 2>&1 | Out-Host
& $pip install -r $Req
if ($LASTEXITCODE -ne 0) {
    Write-Host "[awdui] requirements.txt partial install; applying Python 3.14 OCR fallback"
    & $pip install "rapidocr-onnxruntime==1.2.3"
}
& $pip install pywinauto pyvda comtypes
Write-Host "[awdui] venv ready: $(Join-Path $VenvDir 'Scripts\python.exe')"
& $pip -V

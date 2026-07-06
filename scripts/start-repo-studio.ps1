# Start AwdUI Object Repository Studio (API + optional React dev server).
param(
    [switch]$Dev,
    [int]$ApiPort = 8765
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$VenvPy = Join-Path $env:USERPROFILE ".awdui-mcp\.venv\Scripts\python.exe"
if (-not (Test-Path $VenvPy)) {
    $VenvPy = "python"
}

Write-Host "[repo-studio] Installing API deps if needed..."
& $VenvPy -m pip install -q fastapi uvicorn 2>$null

if ($Dev) {
    $WebDir = Join-Path $Root "repo-web"
    if (Test-Path (Join-Path $WebDir "package.json")) {
        Write-Host "[repo-studio] Starting Vite dev server on http://localhost:5173"
        Start-Process powershell -ArgumentList @(
            "-NoExit", "-Command",
            "Set-Location '$WebDir'; if (-not (Test-Path node_modules)) { npm install }; npm run dev"
        )
    }
} else {
    $Dist = Join-Path $Root "repo-web\dist"
    if (-not (Test-Path $Dist)) {
        Write-Host "[repo-studio] Building SPA (npm install + build)..."
        Push-Location (Join-Path $Root "repo-web")
        if (-not (Test-Path node_modules)) { npm install }
        npm run build
        Pop-Location
    }
}

Write-Host "[repo-studio] API http://127.0.0.1:$ApiPort"
Set-Location $Root
$ApiDir = Join-Path $Root "repo-api"
$ServerDir = Join-Path $Root "mcp-servers\awdui-server"
& $VenvPy -m uvicorn main:app --app-dir $ApiDir --host 127.0.0.1 --port $ApiPort --reload `
    --reload-dir $ApiDir --reload-dir $ServerDir

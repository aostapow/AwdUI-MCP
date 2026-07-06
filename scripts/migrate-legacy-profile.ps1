# Migrate user data from a legacy profile dir into ~/.awdui-mcp.
# Use when upgrading from an old install path/name. Does NOT delete the source
# unless you pass -RemoveSource (after verifying awdui works).
param(
    [string]$Source = (Join-Path $env:USERPROFILE ".handson"),
    [string]$Target = (Join-Path $env:USERPROFILE ".awdui-mcp"),
    [switch]$RemoveSource
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Source)) {
    Write-Error "Source profile not found: $Source"
}

New-Item -ItemType Directory -Force -Path $Target | Out-Null

function Merge-JsonObjectFile {
    param([string]$RelativePath)
    $srcFile = Join-Path $Source $RelativePath
    $dstFile = Join-Path $Target $RelativePath
    if (-not (Test-Path $srcFile)) { return }

    if (-not (Test-Path $dstFile)) {
        Copy-Item $srcFile $dstFile -Force
        Write-Host "[migrate] copied $RelativePath"
        return
    }

    $src = Get-Content $srcFile -Raw | ConvertFrom-Json
    $dst = Get-Content $dstFile -Raw | ConvertFrom-Json
    foreach ($prop in $src.PSObject.Properties) {
        $dst | Add-Member -NotePropertyName $prop.Name -NotePropertyValue $prop.Value -Force
    }
    $dst | ConvertTo-Json -Depth 20 | Set-Content $dstFile -Encoding UTF8
    Write-Host "[migrate] merged $RelativePath"
}

function Merge-Directory {
    param([string]$RelativePath)
    $srcDir = Join-Path $Source $RelativePath
    $dstDir = Join-Path $Target $RelativePath
    if (-not (Test-Path $srcDir)) { return }
    New-Item -ItemType Directory -Force -Path $dstDir | Out-Null
    Copy-Item -Path (Join-Path $srcDir "*") -Destination $dstDir -Recurse -Force
    Write-Host "[migrate] merged directory $RelativePath"
}

Write-Host "[migrate] source: $Source"
Write-Host "[migrate] target: $Target"

Merge-JsonObjectFile "strategy_memory.json"
Merge-JsonObjectFile "version_check.json"
Merge-Directory "repositories"
Merge-Directory "traces"

Write-Host "[migrate] Done. Profile data is under $Target"
Write-Host "[migrate] Recreate venv if needed: scripts\setup-awdui-venv.ps1"

if ($RemoveSource) {
    Remove-Item -Recurse -Force $Source
    Write-Host "[migrate] Removed source profile $Source"
}

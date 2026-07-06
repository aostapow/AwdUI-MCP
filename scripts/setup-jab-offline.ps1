# Instalar Java Access Bridge (JAB) sin internet.
# Archivos descargados previamente en C:\temp (ver nombres abajo).
#
# Copiar al admin:
#   C:\temp\OpenJDK17U-jdk_x64_windows_hotspot_17.0.19_10.msi
#   C:\temp\pyjab-wheels\  (carpeta completa)
#
# Ejecutar PowerShell como Administrador:
#   Set-ExecutionPolicy -Scope Process Bypass -Force
#   & C:\mcps\AwdUI-MCP\scripts\setup-jab-offline.ps1

$ErrorActionPreference = "Stop"

$JdkMsi = "C:\temp\OpenJDK17U-jdk_x64_windows_hotspot_17.0.19_10.msi"
$WheelsDir = "C:\temp\pyjab-wheels"
$JdkDir = "C:\Program Files\Eclipse Adoptium\jdk-17.0.19.10-hotspot"
$AwdUiPy = Join-Path $env:USERPROFILE ".awdui-mcp\.venv\Scripts\python.exe"
$AwdUiServer = "C:\mcps\AwdUI-MCP\mcp-servers\awdui-server"
$McpJson = Join-Path $env:USERPROFILE ".cursor\mcp.json"

if (-not (Test-Path $JdkMsi)) {
    Write-Error "No se encuentra el MSI: $JdkMsi"
}
if (-not (Test-Path $WheelsDir)) {
    Write-Error "No se encuentra la carpeta de wheels: $WheelsDir"
}
if (-not (Test-Path $AwdUiPy)) {
    Write-Error "No se encuentra el venv de awdui: $AwdUiPy"
}

Write-Host "[jab] Instalando JDK desde $JdkMsi"
$msiArgs = @(
    "/i", "`"$JdkMsi`"",
    "ADDLOCAL=FeatureMain,FeatureEnvironment,FeatureJarFileRunWith,FeatureJavaHome",
    "INSTALLDIR=`"$JdkDir`"",
    "/qn"
)
$proc = Start-Process msiexec.exe -ArgumentList $msiArgs -Wait -PassThru
if ($proc.ExitCode -ne 0) {
    Write-Error "msiexec fallo con codigo $($proc.ExitCode)"
}

if (-not (Test-Path "$JdkDir\bin\java.exe")) {
    Write-Error "JDK no quedo en $JdkDir. Revise Get-ChildItem 'C:\Program Files\Eclipse Adoptium'"
}

Write-Host "[jab] JAVA_HOME -> $JdkDir"
[Environment]::SetEnvironmentVariable("JAVA_HOME", $JdkDir, "Machine")
$env:JAVA_HOME = $JdkDir

Write-Host "[jab] Habilitando Java Access Bridge"
& "$JdkDir\bin\jabswitch.exe" -enable

Write-Host "[jab] Instalando pyjab desde $WheelsDir"
& $AwdUiPy -m pip install --no-index --find-links $WheelsDir pyjab

Write-Host "[jab] Verificando check_java_bridge"
& $AwdUiPy -c "import sys; sys.path.insert(0, r'$AwdUiServer'); from detection.backends.jab_backend import check_java_bridge; import json; print(json.dumps(check_java_bridge(), indent=2))"

if (Test-Path $McpJson) {
    $raw = [System.IO.File]::ReadAllText($McpJson)
    if ($raw.Length -ge 3 -and $raw[0] -eq [char]0xFEFF) { $raw = $raw.Substring(1) }
    $javaHomeJson = ($JdkDir -replace '\\', '\\\\')
    if ($raw -match '"JAVA_HOME"\s*:') {
        $raw = [regex]::Replace($raw, '"JAVA_HOME"\s*:\s*"[^"]*"', "`"JAVA_HOME`": `"$javaHomeJson`"")
    } elseif ($raw -match '("awdui"\s*:\s*\{[\s\S]*?"env"\s*:\s*\{)') {
        $raw = [regex]::Replace(
            $raw,
            '("awdui"\s*:\s*\{[\s\S]*?"env"\s*:\s*\{)',
            "`${1}`n        `"JAVA_HOME`": `"$javaHomeJson`","
        )
    }
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($McpJson, $raw, $utf8NoBom)
    Write-Host "[jab] JAVA_HOME agregado en $McpJson"
}

Write-Host "[jab] Listo. Reinicie awdui: & C:\mcps\AwdUI-MCP\scripts\restart-awdui-mcp.ps1"

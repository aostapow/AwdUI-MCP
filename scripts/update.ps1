# Runs python scripts/update.py from the AwdUI install directory.
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $ScriptDir "..")
python (Join-Path $ScriptDir "update.py")

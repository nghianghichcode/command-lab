$ErrorActionPreference = "Stop"

$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$parts = @()

if ($userPath) {
    $parts = $userPath -split ";" | Where-Object { $_ -ne "" }
}

$alreadyInstalled = $parts | Where-Object {
    $_.TrimEnd("\") -ieq $appDir.TrimEnd("\")
}

if (-not $alreadyInstalled) {
    $nextPath = ($parts + $appDir) -join ";"
    [Environment]::SetEnvironmentVariable("Path", $nextPath, "User")
    Write-Host "Installed command path:" $appDir
} else {
    Write-Host "Command path already installed:" $appDir
}

Write-Host ""
Write-Host "Open a new terminal, then run:"
Write-Host "  cmdlab"
Write-Host ""
Write-Host "To launch it in a new Windows Terminal window, run:"
Write-Host "  cmdlab-window"

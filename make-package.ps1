$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$dist = Join-Path $root "dist"
$zipPath = Join-Path $dist "command-lab.zip"

New-Item -ItemType Directory -Force -Path $dist | Out-Null

if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

$files = @(
    "terminal_ui.py",
    "cmdlab.cmd",
    "cmdlab-window.cmd",
    "run.cmd",
    "install-command.ps1",
    "README.md"
)

$paths = $files | ForEach-Object { Join-Path $root $_ }
Compress-Archive -Path $paths -DestinationPath $zipPath -Force

Write-Host "Package created:"
Write-Host "  $zipPath"
Write-Host ""
Write-Host "Upload this zip file somewhere public, then put its URL into install-online.ps1."

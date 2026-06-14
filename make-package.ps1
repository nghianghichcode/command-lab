$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$dist = Join-Path $root "dist"
$zipPath = Join-Path $dist "command-lab.zip"
$packageDir = Join-Path $dist "package"
$appBuildDir = Join-Path $root "build\exe\cmdlab"
$exePath = Join-Path $appBuildDir "cmdlab.exe"

New-Item -ItemType Directory -Force -Path $dist | Out-Null

if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

if (-not (Test-Path $exePath)) {
    & powershell -ExecutionPolicy Bypass -File (Join-Path $root "build-exe.ps1")
}

if (Test-Path $packageDir) {
    Remove-Item -Recurse -Force $packageDir
}

New-Item -ItemType Directory -Force -Path $packageDir | Out-Null

$files = @(
    "terminal_ui.py",
    "cmdlab.cmd",
    "cmdlab-window.cmd",
    "run.cmd",
    "install-command.ps1",
    "README.md"
)

foreach ($file in $files) {
    $source = Join-Path $root $file
    Copy-Item -Force -Path $source -Destination (Join-Path $packageDir (Split-Path -Leaf $file))
}

Copy-Item -Recurse -Force -Path (Join-Path $appBuildDir "*") -Destination $packageDir

Compress-Archive -Path (Join-Path $packageDir "*") -DestinationPath $zipPath -Force

Write-Host "Package created:"
Write-Host "  $zipPath"
Write-Host ""
Write-Host "Upload this zip file somewhere public, then put its URL into install-online.ps1."

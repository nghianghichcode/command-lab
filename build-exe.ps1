$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$buildRoot = Join-Path $root "build"
$exeDist = Join-Path $buildRoot "exe"
$appDir = Join-Path $exeDist "pctool"
$pyinstallerWork = Join-Path $buildRoot "pyinstaller"
$exePath = Join-Path $appDir "pctool.exe"

New-Item -ItemType Directory -Force -Path $buildRoot | Out-Null

if (Test-Path $exeDist) {
    Remove-Item -Recurse -Force $exeDist
}

python -m PyInstaller `
    --name pctool `
    --clean `
    --distpath $exeDist `
    --workpath $pyinstallerWork `
    --specpath $buildRoot `
    (Join-Path $root "terminal_ui.py")

if (-not (Test-Path $exePath)) {
    throw "Build failed: cmdlab.exe was not created."
}

Write-Host "Executable created:"
Write-Host "  $exePath"

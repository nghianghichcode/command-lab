$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$dist = Join-Path $root "dist"
$zipPath = Join-Path $dist "command-lab.zip"
$packageDir = Join-Path $dist ("package-" + [guid]::NewGuid().ToString("N"))
$exePath = Join-Path $root "pctool.exe"

New-Item -ItemType Directory -Force -Path $dist | Out-Null

if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

# Build onefile exe
python -m PyInstaller --name pctool --onefile --clean `
    --distpath $root `
    --workpath (Join-Path $root "build\pyinstaller") `
    --specpath (Join-Path $root "build") `
    (Join-Path $root "terminal_ui.py")

New-Item -ItemType Directory -Force -Path $packageDir | Out-Null

$files = @(
    "terminal_ui.py",
    "pctool.cmd",
    "pctool-window.cmd",
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

Copy-Item -Force -Path $exePath -Destination (Join-Path $packageDir "pctool.exe")

Start-Sleep -Milliseconds 500
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    $packageDir,
    $zipPath,
    [System.IO.Compression.CompressionLevel]::Optimal,
    $false
)

Write-Host "Package created:"
Write-Host "  $zipPath"
Write-Host ""
Write-Host "Upload this zip file somewhere public, then put its URL into install-online.ps1."

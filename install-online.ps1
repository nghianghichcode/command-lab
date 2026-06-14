$ErrorActionPreference = "Stop"

# Upload dist/command-lab.zip to this repository's GitHub Releases.
$ZipUrl = "https://github.com/nghianghichcode/command-lab/releases/latest/download/command-lab.zip?v=pctool-screen-20260614"

$InstallDir = Join-Path $env:LOCALAPPDATA "NghiaPCToolkit"
$TempDir = Join-Path $env:TEMP ("command-lab-install-" + [guid]::NewGuid().ToString("N"))
$ZipPath = Join-Path $TempDir "command-lab.zip"

if ($ZipUrl -eq "https://example.com/command-lab.zip") {
    Write-Host "Set the real download URL in install-online.ps1 first."
    Write-Host "Example URL: https://github.com/nghianghichcode/command-lab/releases/latest/download/command-lab.zip"
    exit 1
}

New-Item -ItemType Directory -Force -Path $TempDir | Out-Null
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

try {
    Write-Host "Downloading Nghia PC Toolkit..."
    Invoke-WebRequest -UseBasicParsing -Uri $ZipUrl -OutFile $ZipPath

    Write-Host "Installing to $InstallDir..."
    Expand-Archive -Force -Path $ZipPath -DestinationPath $InstallDir

    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $parts = @()

    if ($userPath) {
        $parts = $userPath -split ";" | Where-Object { $_ -ne "" }
    }

    $alreadyInstalled = $parts | Where-Object {
        $_.TrimEnd("\") -ieq $InstallDir.TrimEnd("\")
    }

    if (-not $alreadyInstalled) {
        $nextPath = ($parts + $InstallDir) -join ";"
        [Environment]::SetEnvironmentVariable("Path", $nextPath, "User")
    }

    Write-Host ""
    Write-Host "Installed."
    Write-Host "For later use, open a new terminal and run:"
    Write-Host "  pctool"
    Write-Host ""
    Write-Host "Or open a new terminal window with:"
    Write-Host "  pctool-window"
    Write-Host ""
    Write-Host "Legacy aliases also work:"
    Write-Host "  cmdlab"

    $launcher = Join-Path $InstallDir "pctool-window.cmd"
    if (Test-Path $launcher) {
        Write-Host ""
        Write-Host "Opening Nghia PC Toolkit..."
        Start-Process -FilePath $launcher
    }
} finally {
    if (Test-Path $TempDir) {
        Remove-Item -Recurse -Force $TempDir
    }
}

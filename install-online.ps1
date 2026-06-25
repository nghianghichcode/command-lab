$ErrorActionPreference = "Stop"

# Upload dist/command-lab.zip to this repository's GitHub Releases.
$ZipUrl = "https://github.com/nghianghichcode/command-lab/releases/latest/download/command-lab.zip?v=pctool-v060-20260625"

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
    Write-Host "Đang tải Nghia PC Toolkit..."
    Invoke-WebRequest -UseBasicParsing -Uri $ZipUrl -OutFile $ZipPath

    Write-Host "Đang cài đặt vào $InstallDir..."
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
    Write-Host "Đã cài đặt thành công!"
    Write-Host "Từ giờ, mở terminal mới và gõ:"
    Write-Host "  pctool"
    Write-Host ""
    Write-Host "Hoặc mở trong một cửa sổ riêng:"
    Write-Host "  pctool-window"
    Write-Host ""
    Write-Host "Các lệnh cũ vẫn dùng được:"
    Write-Host "  cmdlab"

    $launcher = Join-Path $InstallDir "pctool-window.cmd"
    if (Test-Path $launcher) {
        Write-Host ""
        Write-Host "Đang mở Nghia PC Toolkit..."
        Start-Process -FilePath $launcher
    }
} finally {
    if (Test-Path $TempDir) {
        Remove-Item -Recurse -Force $TempDir
    }
}

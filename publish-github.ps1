$ErrorActionPreference = "Stop"

$RepoOwner = "nghianghichcode"
$RepoName = "command-lab"
$ReleaseTag = "v0.1.0"
$ReleaseTitle = "Command Lab v0.1.0"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$zipPath = Join-Path $root "dist\command-lab.zip"

function Get-GhPath {
    $cmd = Get-Command gh -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    $programFilesPath = "C:\Program Files\GitHub CLI\gh.exe"
    if (Test-Path $programFilesPath) {
        return $programFilesPath
    }

    throw "GitHub CLI not found. Install it first: winget install --id GitHub.cli -e --source winget"
}

function Invoke-QuietNative {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock] $Command
    )

    $oldErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $Command *> $null
        return $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $oldErrorActionPreference
    }
}

$gh = Get-GhPath

Push-Location $root
try {
    & $gh auth status | Out-Host

    & powershell -ExecutionPolicy Bypass -File (Join-Path $root "make-package.ps1")

    $repoExists = (Invoke-QuietNative { & $gh repo view "$RepoOwner/$RepoName" }) -eq 0

    if (-not $repoExists) {
        & $gh repo create "$RepoOwner/$RepoName" --public --description "Interactive command terminal prototype" --disable-wiki
    }

    $remoteUrl = "https://github.com/$RepoOwner/$RepoName.git"
    $hasOrigin = (Invoke-QuietNative { git remote get-url origin }) -eq 0

    if (-not $hasOrigin) {
        git remote add origin $remoteUrl
    } else {
        $origin = git remote get-url origin
        if ($origin -ne $remoteUrl) {
            git remote set-url origin $remoteUrl
        }
    }

    git push -u origin main

    $releaseExists = (Invoke-QuietNative { & $gh release view $ReleaseTag --repo "$RepoOwner/$RepoName" }) -eq 0
    if (-not $releaseExists) {
        & $gh release create $ReleaseTag $zipPath --repo "$RepoOwner/$RepoName" --title $ReleaseTitle --notes "Initial Windows command terminal installer."
    } else {
        & $gh release upload $ReleaseTag $zipPath --repo "$RepoOwner/$RepoName" --clobber
    }

    Write-Host ""
    Write-Host "Published:"
    Write-Host "  https://github.com/$RepoOwner/$RepoName"
    Write-Host ""
    Write-Host "User install command:"
    Write-Host "  powershell -NoProfile -ExecutionPolicy Bypass -Command `"irm https://raw.githubusercontent.com/$RepoOwner/$RepoName/main/install-online.ps1 | iex`""
} finally {
    Pop-Location
}

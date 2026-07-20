#Requires -Version 5.1
<#
.SYNOPSIS
    Build a distributable zip for the QGIS plugin repository / "Install from ZIP".

.DESCRIPTION
    Produces dist\topology_split-<version>.zip with the plugin nested under a
    top-level "topology_split/" folder (as required by QGIS), excluding dev files.
    The version is read from metadata.txt.

.EXAMPLE
    ./scripts/package.ps1
#>
param()

$ErrorActionPreference = "Stop"

$PluginName = "network_topology"
$RepoRoot   = Split-Path -Parent $PSScriptRoot
$DistDir    = Join-Path $RepoRoot "dist"
$StageDir   = Join-Path $DistDir $PluginName

# --- read version from metadata.txt ---
$metadata = Get-Content (Join-Path $RepoRoot "metadata.txt")
$versionLine = $metadata | Where-Object { $_ -match "^\s*version\s*=" } | Select-Object -First 1
if (-not $versionLine) { throw "version= not found in metadata.txt" }
$Version = ($versionLine -split "=", 2)[1].Trim()

$ZipPath = Join-Path $DistDir "$PluginName-$Version.zip"
Write-Host "Packaging $PluginName $Version -> $ZipPath"

# --- stage a clean copy ---
if (Test-Path $StageDir) { Remove-Item -Recurse -Force $StageDir }
New-Item -ItemType Directory -Force -Path $StageDir | Out-Null

$Exclude = @(
    ".git", ".github", ".claude", "scripts", "tests", "docs", "dist",
    "__pycache__", ".pytest_cache", ".ruff_cache",
    ".gitignore", "requirements-dev.txt", "pyproject.toml", "CLAUDE.md"
)

Get-ChildItem -Path $RepoRoot -Force | Where-Object { $Exclude -notcontains $_.Name } | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination $StageDir -Recurse -Force
}

# --- zip it (top-level folder = plugin name) ---
if (Test-Path $ZipPath) { Remove-Item -Force $ZipPath }
Compress-Archive -Path $StageDir -DestinationPath $ZipPath -Force
Remove-Item -Recurse -Force $StageDir

Write-Host "Built $ZipPath" -ForegroundColor Green

#Requires -Version 5.1
<#
.SYNOPSIS
    Copy this plugin into a local QGIS 4 profile for manual testing.

.DESCRIPTION
    Copies the plugin source (excluding dev-only files) into
    <profile>\python\plugins\topology_split.

    After deploying: enable "Network Topology" in the Plugin Manager, and install the
    "Plugin Reloader" plugin to reload code changes without restarting QGIS.

.PARAMETER Profile
    QGIS profile name. Default: "default".

.PARAMETER PluginsRoot
    Override the plugins directory entirely (skips profile lookup). Use this if your
    QGIS 4 profile lives somewhere non-standard.

.EXAMPLE
    ./scripts/deploy.ps1
    ./scripts/deploy.ps1 -Profile myprofile
#>
param(
    [string]$Profile = "default",
    [string]$PluginsRoot
)

$ErrorActionPreference = "Stop"

$PluginName = "network_topology"
$SourceDir  = Split-Path -Parent $PSScriptRoot   # repo root (parent of scripts/)

if (-not $PluginsRoot) {
    # QGIS 4.x uses the "QGIS4" profiles folder (QGIS 3.x used "QGIS3").
    # If your install uses a different location, pass -PluginsRoot explicitly.
    $PluginsRoot = Join-Path $env:APPDATA "QGIS\QGIS4\profiles\$Profile\python\plugins"
}

$Target = Join-Path $PluginsRoot $PluginName
Write-Host "Source : $SourceDir"
Write-Host "Target : $Target"

if (-not (Test-Path $PluginsRoot)) {
    New-Item -ItemType Directory -Force -Path $PluginsRoot | Out-Null
}
if (Test-Path $Target) {
    Remove-Item -Recurse -Force $Target
}
New-Item -ItemType Directory -Force -Path $Target | Out-Null

# Files/dirs that should NOT ship into the QGIS profile.
$Exclude = @(
    ".git", ".github", ".claude", "scripts", "tests", "docs",
    "__pycache__", ".pytest_cache", ".ruff_cache",
    ".gitignore", "requirements-dev.txt", "pyproject.toml", "CLAUDE.md"
)

Get-ChildItem -Path $SourceDir -Force | Where-Object { $Exclude -notcontains $_.Name } | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination $Target -Recurse -Force
}

Write-Host "Deployed '$PluginName' to profile '$Profile'." -ForegroundColor Green
Write-Host "Enable it in QGIS: Plugins -> Manage and Install Plugins." -ForegroundColor Green

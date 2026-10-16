# ===============================================================
# WorkStatus - New Page Scaffolder (v3 - template-based)
# Usage: .\new-page.ps1 reports "Reports Dashboard"
# ===============================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$PageId,

    [Parameter(Mandatory=$true)]
    [string]$PageTitle
)

$ErrorActionPreference = "Stop"

$root        = Split-Path -Parent $PSScriptRoot
$frontendDir = Join-Path $root "frontend"
$pagesJsDir  = Join-Path $frontendDir "js\pages"
$templateDir = Join-Path $PSScriptRoot "templates"

if (-not (Test-Path $frontendDir)) {
    Write-Host "[ERROR] Frontend folder not found: $frontendDir" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $pagesJsDir)) {
    New-Item -ItemType Directory -Path $pagesJsDir | Out-Null
    Write-Host "[OK] Created folder: js\pages" -ForegroundColor Cyan
}

$htmlPath = Join-Path $frontendDir "$PageId.html"
$jsPath   = Join-Path $pagesJsDir "$PageId.js"

if (Test-Path $htmlPath) {
    Write-Host "[ERROR] Page already exists: $htmlPath" -ForegroundColor Red
    exit 1
}

# Read templates
$htmlTemplate = Get-Content (Join-Path $templateDir "page-template.html") -Raw -Encoding UTF8
$jsTemplate   = Get-Content (Join-Path $templateDir "page-template.js")   -Raw -Encoding UTF8

# Replace placeholders
$htmlContent = $htmlTemplate.Replace("{{TITLE}}", $PageTitle).Replace("{{ID}}", $PageId)
$jsContent   = $jsTemplate.Replace("{{TITLE}}", $PageTitle).Replace("{{ID}}", $PageId)

# Write files with UTF-8 no BOM
[System.IO.File]::WriteAllText($htmlPath, $htmlContent, (New-Object System.Text.UTF8Encoding $false))
[System.IO.File]::WriteAllText($jsPath,   $jsContent,   (New-Object System.Text.UTF8Encoding $false))

Write-Host ""
Write-Host "[DONE] Page '$PageId' created:" -ForegroundColor Green
Write-Host "  $htmlPath" -ForegroundColor Gray
Write-Host "  $jsPath" -ForegroundColor Gray
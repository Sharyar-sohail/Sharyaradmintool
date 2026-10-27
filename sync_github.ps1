<#
.SYNOPSIS
    ApexSys Quick GitHub Sync Utility
.DESCRIPTION
    Stages all modified files, commits with a message, pulls remote changes,
    and pushes directly to GitHub main branch to trigger instant Streamlit Cloud rebuilds.
.EXAMPLE
    .\sync_github.ps1 "Add new hardware diagnostic card"
#>

param(
    [string]$Message = ""
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   APEXSYS GITHUB CONTINUOUS SYNC" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

# 1. Check if git repository exists
if (-not (Test-Path ".git")) {
    Write-Error "Not a git repository. Please initialize git first."
    exit 1
}

# 2. Check for changes
$status = git status --porcelain
if (-not $status) {
    Write-Host "[*] No local changes detected. Working tree is clean." -ForegroundColor Yellow
    Write-Host "[*] Pulling latest remote changes just in case..." -ForegroundColor Cyan
    git pull origin main
    exit 0
}

# 3. Generate commit message if empty
if (-not $Message) {
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $Message = "Auto-sync update: $timestamp"
}

# 4. Stage, commit, pull, and push
try {
    Write-Host "[1/4] Staging modified files (git add .)..." -ForegroundColor Cyan
    git add .

    Write-Host "[2/4] Committing changes: '$Message'..." -ForegroundColor Cyan
    git commit -m "$Message"

    Write-Host "[3/4] Pulling remote updates with rebase..." -ForegroundColor Cyan
    git pull --rebase origin main

    Write-Host "[4/4] Pushing to origin main..." -ForegroundColor Green
    git push origin main

    Write-Host "`n[SUCCESS] Successfully synchronized with GitHub main branch!" -ForegroundColor Green
    Write-Host "[*] Streamlit Community Cloud will automatically detect the push and deploy." -ForegroundColor Cyan
} catch {
    Write-Warning "[!] Git push encountered an issue: $_"
    Write-Host "Tip: If authentication is required, ensure your GitHub token or Git Credential Manager is active." -ForegroundColor Yellow
}

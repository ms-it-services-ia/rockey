# Git extension: initialize-repo.ps1
# Initializes a Git repository for a brand-new Spec Kit project (before_constitution hook).
# Safe to run on an existing repository — it no-ops rather than re-initializing.

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir "git-common.ps1")

$RepoRoot = Find-SkProjectRoot -StartDir $ScriptDir
if (-not $RepoRoot) { $RepoRoot = (Get-Location).Path }
Set-Location $RepoRoot

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Warning "[specify] Git not found; skipped repository initialization"
    exit 0
}

git rev-parse --is-inside-work-tree 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Warning "[specify] Already inside a Git repository; skipped initialization"
    exit 0
}

$ConfigFile = Join-Path $RepoRoot ".specify/extensions/git/git-config.yml"
$CommitMessage = Get-SkYamlScalar -Path $ConfigFile -Key "init_commit_message"
if (-not $CommitMessage) { $CommitMessage = "[Spec Kit] Initial commit" }

git init | Out-Null
git add . | Out-Null
git commit -q -m $CommitMessage | Out-Null

Write-Output "[OK] Git repository initialized"

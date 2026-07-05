# Git extension: create-new-feature.ps1
# Creates and checks out a git branch for a new Spec Kit feature (branch creation only).
#
# Usage: create-new-feature.ps1 [-Json] [-Timestamp] [-ShortName <name>] <feature description>
#
# Honors the GIT_BRANCH_NAME environment variable: when set, it is used verbatim as the
# branch name, bypassing all prefix/short-name generation.

param(
    [switch]$Json,
    [switch]$Timestamp,
    [string]$ShortName = "",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$FeatureDescriptionParts
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir "git-common.ps1")

$RepoRoot = Find-SkProjectRoot -StartDir $ScriptDir
if (-not $RepoRoot) { $RepoRoot = (Get-Location).Path }
Set-Location $RepoRoot

$ConfigFile = Join-Path $RepoRoot ".specify/extensions/git/git-config.yml"
$InitOptionsFile = Join-Path $RepoRoot ".specify/init-options.json"

if ($env:GIT_BRANCH_NAME) {
    $BranchName = $env:GIT_BRANCH_NAME
    if ($BranchName -match "^(\d+)") {
        $FeatureNum = $Matches[1]
    } else {
        $FeatureNum = $BranchName
    }
} else {
    if (-not $ShortName) {
        Write-Error "Error: -ShortName is required unless GIT_BRANCH_NAME is set"
        exit 1
    }

    $Slug = ($ShortName.ToLower() -replace '[ _]', '-') -replace '[^a-z0-9-]', ''
    $Slug = ($Slug -replace '-+', '-').Trim('-')

    $NumberingMode = Get-SkYamlScalar -Path $ConfigFile -Key "branch_numbering"
    if (-not $NumberingMode) { $NumberingMode = Get-SkJsonScalar -Path $InitOptionsFile -Key "branch_numbering" }
    if (-not $NumberingMode) { $NumberingMode = "sequential" }
    if ($Timestamp) { $NumberingMode = "timestamp" }

    if ($NumberingMode -eq "timestamp") {
        $Prefix = Get-Date -Format "yyyyMMdd-HHmmss"
        $FeatureNum = $Prefix
    } else {
        $Highest = 0
        $SpecsDir = Join-Path $RepoRoot "specs"
        if (Test-Path $SpecsDir) {
            Get-ChildItem $SpecsDir -Directory | ForEach-Object {
                if ($_.Name -match "^(\d{3,})-") {
                    $n = [int]$Matches[1]
                    if ($n -gt $Highest) { $Highest = $n }
                }
            }
        }
        if (Test-SkHasGit) {
            git branch -a 2>$null | ForEach-Object {
                $name = $_ -replace '^\*?\s*', '' -replace '^remotes/[^/]+/', ''
                if ($name -match "^(\d{3,})-") {
                    $n = [int]$Matches[1]
                    if ($n -gt $Highest) { $Highest = $n }
                }
            }
        }
        $Prefix = "{0:D3}" -f ($Highest + 1)
        $FeatureNum = $Prefix
    }

    $BranchName = "$Prefix-$Slug"
}

if (Test-SkHasGit) {
    git rev-parse --verify $BranchName 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        git checkout $BranchName | Out-Null
    } else {
        git checkout -b $BranchName | Out-Null
    }
} else {
    Write-Warning "[specify] Git repository not detected; skipped branch creation"
}

if ($Json) {
    [PSCustomObject]@{ BRANCH_NAME = $BranchName; FEATURE_NUM = $FeatureNum } | ConvertTo-Json -Compress
} else {
    Write-Output "BRANCH_NAME=$BranchName"
    Write-Output "FEATURE_NUM=$FeatureNum"
}

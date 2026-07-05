# Git extension: git-common.ps1
# Shared helper functions for the git extension's scripts (create-new-feature.ps1,
# initialize-repo.ps1). Dot-source this file; it is not meant to be executed directly.

function Find-SkProjectRoot {
    param([string]$StartDir = (Get-Location).Path)
    $dir = Resolve-Path $StartDir
    while ($true) {
        if ((Test-Path (Join-Path $dir ".specify")) -or (Test-Path (Join-Path $dir ".git"))) {
            return $dir
        }
        $parent = Split-Path $dir -Parent
        if (-not $parent -or $parent -eq $dir) { return $null }
        $dir = $parent
    }
}

function Test-SkHasGit {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { return $false }
    git rev-parse --is-inside-work-tree 2>$null | Out-Null
    return ($LASTEXITCODE -eq 0)
}

function Get-SkYamlScalar {
    param([string]$Path, [string]$Key)
    if (-not (Test-Path $Path)) { return "" }
    $line = Get-Content $Path | Where-Object { $_ -match "^${Key}:\s*(.*)$" } | Select-Object -First 1
    if (-not $line) { return "" }
    $value = [regex]::Match($line, "^${Key}:\s*(.*)$").Groups[1].Value.Trim()
    return $value.Trim('"').Trim("'")
}

function Get-SkJsonScalar {
    param([string]$Path, [string]$Key)
    if (-not (Test-Path $Path)) { return "" }
    try {
        $json = Get-Content $Path -Raw | ConvertFrom-Json
        if ($json.PSObject.Properties.Name -contains $Key) { return [string]$json.$Key }
    } catch { }
    return ""
}

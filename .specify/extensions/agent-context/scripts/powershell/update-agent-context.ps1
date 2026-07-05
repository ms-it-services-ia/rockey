# Agent-context extension: update-agent-context.ps1
# Refreshes the managed Spec Kit section inside the active coding agent's context file
# (e.g. CLAUDE.md) so it points at the most recently created feature's plan.md.
#
# Usage: update-agent-context.ps1 [plan_path]

param(
    [string]$PlanPath = ""
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Find-ProjectRoot {
    param([string]$StartDir)
    $dir = Resolve-Path $StartDir
    while ($true) {
        if (Test-Path (Join-Path $dir ".specify")) { return $dir }
        $parent = Split-Path $dir -Parent
        if (-not $parent -or $parent -eq $dir) { return $null }
        $dir = $parent
    }
}

$RepoRoot = Find-ProjectRoot -StartDir $ScriptDir
if (-not $RepoRoot) { $RepoRoot = (Get-Location).Path }
Set-Location $RepoRoot

$ConfigFile = Join-Path $RepoRoot ".specify/extensions/agent-context/agent-context-config.yml"
$ContextFile = ""
$MarkerStart = "<!-- SPECKIT START -->"
$MarkerEnd = "<!-- SPECKIT END -->"

if (Test-Path $ConfigFile) {
    foreach ($line in Get-Content $ConfigFile) {
        if ($line -match "^context_file:\s*(.*)$") { $ContextFile = $Matches[1].Trim() }
        if ($line -match "^\s+start:\s*(.*)$") { $MarkerStart = $Matches[1].Trim() }
        if ($line -match "^\s+end:\s*(.*)$") { $MarkerEnd = $Matches[1].Trim() }
    }
}

if (-not $ContextFile) {
    Write-Warning "[specify] No context_file configured; nothing to do"
    exit 0
}

$ContextPath = Join-Path $RepoRoot $ContextFile
if (-not (Test-Path $ContextPath)) {
    Write-Warning "[specify] Context file '$ContextFile' not found; nothing to do"
    exit 0
}

if (-not $PlanPath) {
    $latest = Get-ChildItem -Path (Join-Path $RepoRoot "specs") -Filter "plan.md" -Recurse -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($latest) { $PlanPath = $latest.FullName }
}

if (-not $PlanPath) {
    Write-Warning "[specify] No plan.md found under specs/; nothing to do"
    exit 0
}

$PlanRel = $PlanPath.Replace("$RepoRoot\", "").Replace("$RepoRoot/", "").Replace('\', '/')

$Block = @"
$MarkerStart
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:
$PlanRel
$MarkerEnd
"@

$content = Get-Content $ContextPath -Raw -ErrorAction SilentlyContinue
if ($content -and $content.Contains($MarkerStart)) {
    $pattern = [regex]::Escape($MarkerStart) + "[\s\S]*?" + [regex]::Escape($MarkerEnd)
    Set-Content -Path $ContextPath -Value ([regex]::Replace($content, $pattern, $Block)) -NoNewline
} else {
    Add-Content -Path $ContextPath -Value "`n$Block"
}

Write-Output "[OK] Agent context updated: $ContextFile -> $PlanRel"

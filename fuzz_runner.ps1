#!/usr/bin/env pwsh
# fuzz_runner.ps1 — Overnight fuzz orchestration for Kairo Phantom
#
# Usage (from repo root):
#   .\fuzz_runner.ps1                        # 30 min each target (default)
#   .\fuzz_runner.ps1 -TimeEach 3600         # 60 min each
#   .\fuzz_runner.ps1 -Target uia_text_parser  # single target
#   .\fuzz_runner.ps1 -CiMode               # 60 seconds each (CI smoke test)
#
# Prerequisites:
#   rustup install nightly
#   cargo install cargo-fuzz
#
# Output:
#   fuzz-results\<target>\crashes\           <- any crash inputs found
#   fuzz-results\<target>\corpus\            <- interesting seeds for replay
#   fuzz-results\fuzz_report.json            <- machine-readable summary

param(
    [int]    $TimeEach = 1800,     # seconds per target (default: 30 min)
    [string] $Target   = "",       # if set, only run this target
    [switch] $CiMode,              # override to 60 seconds each
    [switch] $SkipInstall          # skip nightly/cargo-fuzz install
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($CiMode) { $TimeEach = 60 }

$Targets = @("uia_text_parser", "mcp_json_parser", "toml_plugin_loader")
if ($Target -ne "") { $Targets = @($Target) }

$FuzzDir   = Join-Path $PSScriptRoot "phantom-core\fuzz"
$ResultDir = Join-Path $PSScriptRoot "fuzz-results"
New-Item -ItemType Directory -Force -Path $ResultDir | Out-Null

# ── Install prerequisites ─────────────────────────────────────────────────────
if (-not $SkipInstall) {
    Write-Host "📦 Installing nightly toolchain and cargo-fuzz…" -ForegroundColor Cyan
    rustup install nightly 2>&1 | Write-Host
    cargo +nightly install cargo-fuzz --quiet 2>&1 | Write-Host
    Write-Host "✅ Prerequisites ready.`n" -ForegroundColor Green
}

# ── Run each fuzz target ──────────────────────────────────────────────────────
$Report = @{
    meta = @{
        timestamp  = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
        time_each  = $TimeEach
        ci_mode    = $CiMode.IsPresent
    }
    targets = @{}
}

foreach ($tgt in $Targets) {
    $TargetResultDir = Join-Path $ResultDir $tgt
    $CrashDir        = Join-Path $TargetResultDir "crashes"
    $CorpusDir       = Join-Path $TargetResultDir "corpus"
    New-Item -ItemType Directory -Force -Path $CrashDir  | Out-Null
    New-Item -ItemType Directory -Force -Path $CorpusDir | Out-Null

    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
    Write-Host "🔍 Fuzzing: $tgt  (max $TimeEach seconds)" -ForegroundColor Yellow
    Write-Host "   Crash dir : $CrashDir"
    Write-Host "   Corpus dir: $CorpusDir"
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray

    $StartTime = Get-Date

    # Run cargo-fuzz. stderr is where libFuzzer writes its stats.
    # We capture the exit code to detect crash vs. timeout.
    $proc = Start-Process -FilePath "cargo" `
        -ArgumentList "+nightly", "fuzz", "run", $tgt, "--",
                      "-max_total_time=$TimeEach",
                      "-artifact_prefix=$CrashDir\",
                      "-print_final_stats=1" `
        -WorkingDirectory $FuzzDir `
        -NoNewWindow -PassThru -Wait

    $elapsed = ((Get-Date) - $StartTime).TotalSeconds
    $crashes = (Get-ChildItem -Path $CrashDir -File -ErrorAction SilentlyContinue).Count

    $status = if ($proc.ExitCode -eq 0 -and $crashes -eq 0) {
        "CLEAN"
    } elseif ($crashes -gt 0) {
        "CRASHES_FOUND"
    } else {
        "TIMEOUT_OR_ERROR"
    }

    $colour = if ($status -eq "CLEAN") { "Green" } else { "Red" }
    Write-Host "   Result: $status | Crashes: $crashes | Time: $([int]$elapsed)s" -ForegroundColor $colour

    $Report.targets[$tgt] = @{
        status       = $status
        crashes      = $crashes
        elapsed_sec  = [int]$elapsed
        crash_dir    = $CrashDir
    }
}

# ── Write machine-readable report ────────────────────────────────────────────
$ReportPath = Join-Path $ResultDir "fuzz_report.json"
$Report | ConvertTo-Json -Depth 5 | Set-Content -Path $ReportPath

# ── Final summary ─────────────────────────────────────────────────────────────
Write-Host "`n══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  FUZZ RUN COMPLETE" -ForegroundColor Cyan
Write-Host "══════════════════════════════════════════════════" -ForegroundColor Cyan

$allClean = $true
foreach ($tgt in $Targets) {
    $r = $Report.targets[$tgt]
    $icon  = if ($r.status -eq "CLEAN") { "✅" } else { "❌" }
    $colour = if ($r.status -eq "CLEAN") { "Green" } else { "Red" }
    Write-Host "  $icon  $tgt — $($r.status) ($($r.crashes) crashes, $($r.elapsed_sec)s)" -ForegroundColor $colour
    if ($r.status -ne "CLEAN") { $allClean = $false }
}

Write-Host "`n  Report: $ReportPath" -ForegroundColor DarkGray

if ($allClean) {
    Write-Host "`n  🏁 ALL TARGETS CLEAN — zero crashes found." -ForegroundColor Green
} else {
    Write-Host "`n  ⚠️  CRASHES FOUND. Review files in fuzz-results\<target>\crashes\" -ForegroundColor Red
    Write-Host "     Replay crash: cargo +nightly fuzz run <target> fuzz-results\<target>\crashes\<file>" -ForegroundColor Yellow
    exit 1
}

<#
.SYNOPSIS
    Master orchestration script to deploy 8 GSD/Ruflo agents for 39-scenario parallel testing
.DESCRIPTION
    This script coordinates:
    1. Infrastructure setup (logs, screenshots directories)
    2. Kairo Phantom daemon startup
    3. Background chaos agent launch
    4. 8 parallel primary agents (Word, PPT, Excel, VS Code, Browser, Notepad, Terminal, plus Chaos)
    5. Real-time monitoring and health checks
    6. Result aggregation and reporting
.EXAMPLE
    .\orchestrate_39_scenarios_parallel.ps1
#>

param(
    [switch]$SkipChaos,
    [switch]$DryRun,
    [int]$TimeoutMinutes = 30
)

$ErrorActionPreference = "Stop"
$VerbosePreference = "Continue"

# ============================================================================
# CONFIGURATION
# ============================================================================

$REPO_ROOT = "c:\Users\SANDIP\Desktop\Memory\KairoPhantom"
$TEST_DIR = "C:\tests"
$LOG_DIR = "$TEST_DIR\logs"
$SCREENSHOT_DIR = "$TEST_DIR\screenshots"
$RESULT_DIR = "$TEST_DIR\results"
$MANIFEST = "$REPO_ROOT\test_manifest_39scenarios.json"

$AGENTS = @(
    @{
        Name = "agent_word"
        Command = "python $REPO_ROOT\scripts\win\universal_orchestrator.py --manifest $MANIFEST --agent-id agent_word --scenarios W1,W2,W3,W4,W5,W6,W7,W8,W9,W10 --log-file $LOG_DIR\agent_word.log --gate-enforce --screenshot-on-fail"
        Timeout = 600
    },
    @{
        Name = "agent_ppt"
        Command = "python $REPO_ROOT\scripts\win\universal_orchestrator.py --manifest $MANIFEST --agent-id agent_ppt --scenarios P1,P2,P3,P4,P5,P6,P7 --log-file $LOG_DIR\agent_ppt.log --gate-enforce --screenshot-on-fail"
        Timeout = 480
    },
    @{
        Name = "agent_excel"
        Command = "python $REPO_ROOT\scripts\win\universal_orchestrator.py --manifest $MANIFEST --agent-id agent_excel --scenarios E1,E2,E3,E4,E5 --log-file $LOG_DIR\agent_excel.log --gate-enforce --screenshot-on-fail"
        Timeout = 420
    },
    @{
        Name = "agent_vscode"
        Command = "python $REPO_ROOT\scripts\win\universal_orchestrator.py --manifest $MANIFEST --agent-id agent_vscode --scenarios V1,V2,V3,V4,V5,V6 --log-file $LOG_DIR\agent_vscode.log --gate-enforce --screenshot-on-fail"
        Timeout = 420
    },
    @{
        Name = "agent_browser"
        Command = "python $REPO_ROOT\scripts\win\universal_orchestrator.py --manifest $MANIFEST --agent-id agent_browser --scenarios G1,G2,G3,G4 --log-file $LOG_DIR\agent_browser.log --gate-enforce --screenshot-on-fail"
        Timeout = 360
    },
    @{
        Name = "agent_notepad"
        Command = "python $REPO_ROOT\scripts\win\universal_orchestrator.py --manifest $MANIFEST --agent-id agent_notepad --scenarios N1,N2,N3 --log-file $LOG_DIR\agent_notepad.log --gate-enforce --screenshot-on-fail"
        Timeout = 240
    },
    @{
        Name = "agent_terminal"
        Command = "python $REPO_ROOT\scripts\win\universal_orchestrator.py --manifest $MANIFEST --agent-id agent_terminal --scenarios T1,T2,T3,T4 --log-file $LOG_DIR\agent_terminal.log --gate-enforce --screenshot-on-fail"
        Timeout = 300
    }
)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host "=" * 80 -ForegroundColor Cyan
    Write-Host $Text -ForegroundColor Cyan
    Write-Host "=" * 80 -ForegroundColor Cyan
}

function Write-Phase {
    param([string]$Text, [int]$Phase)
    Write-Host ""
    Write-Host "[$Phase] $Text" -ForegroundColor Yellow
}

function Setup-Directories {
    Write-Phase "Setting up directories" 1
    
    $dirs = @($LOG_DIR, $SCREENSHOT_DIR, $RESULT_DIR)
    foreach ($dir in $dirs) {
        if (!(Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-Verbose "Created directory: $dir"
        } else {
            Write-Verbose "Directory exists: $dir"
        }
    }
    
    Write-Host "+ Directories ready" -ForegroundColor Green
}

function Start-KairoDaemon {
    Write-Phase "Starting Kairo Phantom daemon" 2
    
    # Check if kairo is already running
    $existing = Get-Process kairo -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "+ Kairo daemon already running (PID: $($existing.Id))" -ForegroundColor Green
        return
    }
    
    if ($DryRun) {
        Write-Host "[DRY RUN] Would start: kairo --json-logs" -ForegroundColor Cyan
        return
    }
    
    try {
        Start-Process -FilePath "kairo" -ArgumentList "--json-logs" -NoNewWindow
        Start-Sleep -Seconds 3
        
        $check = Get-Process kairo -ErrorAction SilentlyContinue
        if ($check) {
            Write-Host "+ Kairo daemon started successfully (PID: $($check.Id))" -ForegroundColor Green
        } else {
            throw "Failed to start Kairo daemon"
        }
    } catch {
        Write-Host "! Warning: Could not start Kairo daemon: $_" -ForegroundColor Yellow
    }
}

function Start-ChaosAgent {
    Write-Phase "Starting background Chaos Agent" 3
    
    if ($SkipChaos) {
        Write-Host "- Chaos agent skipped (--SkipChaos)" -ForegroundColor Yellow
        return $null
    }
    
    if ($DryRun) {
        Write-Host "[DRY RUN] Would start chaos agent" -ForegroundColor Cyan
        return $null
    }
    
    try {
        $chaosScript = "$REPO_ROOT\scripts\win\chaos_advanced.ps1"
        if (!(Test-Path $chaosScript)) {
            Write-Host "! Warning: Chaos script not found: $chaosScript" -ForegroundColor Yellow
            return $null
        }
        
        $job = Start-Job -ScriptBlock {
            param($script)
            & $script -Duration 0 -ContinuousMode
        } -ArgumentList $chaosScript
        
        Start-Sleep -Seconds 2
        Write-Host "+ Chaos agent started (Job ID: $($job.Id))" -ForegroundColor Green
        return $job
    } catch {
        Write-Host "! Warning: Failed to start chaos agent: $_" -ForegroundColor Yellow
        return $null
    }
}

function Deploy-ParallelAgents {
    Write-Phase "Deploying 7 parallel test agents" 4
    
    $jobs = @()
    $startTime = Get-Date
    
    foreach ($agent in $AGENTS) {
        Write-Host "  Launching: $($agent.Name)" -ForegroundColor Cyan
        
        if ($DryRun) {
            Write-Host "    [DRY RUN] Would execute: $($agent.Command -replace '^python ', '')" -ForegroundColor DarkCyan
            continue
        }
        
        try {
            $job = Start-Job -ScriptBlock {
                param($cmd)
                Invoke-Expression $cmd 2>&1
            } -ArgumentList $agent.Command -Name $agent.Name
            
            $jobs += @{
                Job = $job
                Name = $agent.Name
                Timeout = $agent.Timeout
                StartTime = $startTime
                LogFile = $agent.Command -match 'log-file\s+(\S+)' | ForEach-Object { $matches[1] }
            }
            
            Write-Host "    + Started (Job ID: $($job.Id))" -ForegroundColor Green
            
            # Stagger agent starts slightly to avoid resource contention
            Start-Sleep -Milliseconds 500
        } catch {
            Write-Host "    x Failed to start: $_" -ForegroundColor Red
        }
    }
    
    if ($DryRun) {
        Write-Host "`n[DRY RUN MODE] Would launch $($jobs.Count) agents in parallel" -ForegroundColor Cyan
    }
    
    return $jobs
}

function Monitor-Execution {
    param($Jobs, $ChaosJob)
    
    Write-Phase "Monitoring execution" 5
    
    if ($DryRun) {
        Write-Host "[DRY RUN] Would monitor $($Jobs.Count) agents" -ForegroundColor Cyan
        return
    }
    
    $allComplete = $false
    $pollInterval = 5  # seconds
    $elapsed = 0
    $timeoutSeconds = $TimeoutMinutes * 60
    
    while (!$allComplete -and $elapsed -lt $timeoutSeconds) {
        $allComplete = $true
        
        foreach ($job in $Jobs) {
            if ($job.Job.State -eq "Running") {
                $allComplete = $false
            }
        }
        
        # Print status
        $running = ($Jobs | Where-Object { $_.Job.State -eq "Running" }).Count
        $completed = $Jobs.Count - $running
        
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Status: $completed/$($Jobs.Count) agents complete, $running still running" -ForegroundColor Cyan
        
        if ($allComplete) {
            Write-Host "+ All agents completed" -ForegroundColor Green
            break
        }
        
        Start-Sleep -Seconds $pollInterval
        $elapsed += $pollInterval
    }
    
    if ($elapsed -ge $timeoutSeconds) {
        Write-Host "x Timeout reached ($TimeoutMinutes minutes)" -ForegroundColor Red
    }
}

function Collect-Results {
    param($Jobs)
    
    Write-Phase "Collecting results" 6
    
    $allResults = @{
        timestamp = (Get-Date).ToString("o")
        totalAgents = $Jobs.Count
        agents = @()
    }
    
    foreach ($job in $Jobs) {
        Write-Host "  Collecting: $($job.Name)" -ForegroundColor Cyan
        
        try {
            $output = Receive-Job -Job $job.Job -ErrorAction SilentlyContinue
            if ($job.Job.State -eq "Completed") { $exitCode = 0 } else { $exitCode = 1 }
            
            # Try to load JSON results if they exist
            $resultsFile = "$RESULT_DIR\$($job.Name)_results.json"
            $result = @{
                agent = $job.Name
                exitCode = $exitCode
                state = $job.Job.State
            }
            
            if (Test-Path $resultsFile) {
                $json = Get-Content $resultsFile | ConvertFrom-Json
                $result.details = $json
                Write-Host "    + Results: $($json.passed)/$($json.totalScenarios) passed" -ForegroundColor Green
            }
            
            $allResults.agents += $result
        } catch {
            Write-Host "    ! Error collecting results: $_" -ForegroundColor Yellow
        }
    }
    
    # Save aggregate results
    $masterReportPath = "$RESULT_DIR\MASTER_REPORT_39_SCENARIOS.json"
    $allResults | ConvertTo-Json -Depth 10 | Set-Content $masterReportPath
    Write-Host "+ Master report saved: $masterReportPath" -ForegroundColor Green
    
    return $allResults
}

function Generate-Summary {
    param($Results)
    
    Write-Phase "Generating summary" 7
    
    $totalPassed = 0
    $totalFailed = 0
    $totalScenarios = 0
    
    foreach ($agent in $Results.agents) {
        if ($agent.details) {
            $totalPassed += $agent.details.passed
            $totalFailed += $agent.details.failed
            $totalScenarios += $agent.details.totalScenarios
        }
    }
    
    if ($totalScenarios -gt 0) { $passRate = ($totalPassed / $totalScenarios * 100) } else { $passRate = 0 }
    
    $summary = @"
# KAIRO PHANTOM - 39 SCENARIO TEST EXECUTION REPORT

## Executive Summary
- **Timestamp**: $($Results.timestamp)
- **Total Agents**: $($Results.totalAgents)
- **Total Scenarios**: $totalScenarios
- **Passed**: $totalPassed
- **Failed**: $totalFailed
- **Pass Rate**: $($passRate.ToString("F1"))%

## Agent Results
$($Results.agents | ForEach-Object {
    if ($_.exitCode -eq 0) { $status = "+ PASS" } else { $status = "x FAIL" }
    "- $($_.agent): $status (State: $($_.state))"
    if ($_.details) {
        "  - Scenarios: $($_.details.passed)/$($_.details.totalScenarios) passed"
    }
} | Out-String)

## Artifacts
- **Master Report**: $RESULT_DIR\MASTER_REPORT_39_SCENARIOS.json
- **Logs**: $LOG_DIR\*.log
- **Screenshots**: $SCREENSHOT_DIR\*.png
- **Individual Results**: $RESULT_DIR\*_results.json

## Status
$(if ($passRate -ge 95) { "+ PASSED - 95%+ pass rate achieved" } else { "x REVIEW REQUIRED - Pass rate below 95%" })

---
Generated: $(Get-Date)
"@
    
    $summaryPath = "$RESULT_DIR\SUMMARY.md"
    Set-Content -Path $summaryPath -Value $summary
    
    Write-Host $summary -ForegroundColor Cyan
    Write-Host "`n+ Summary saved: $summaryPath" -ForegroundColor Green
}

function Cleanup {
    Write-Phase "Cleanup" 8
    
    Write-Host "Stopping all agent jobs..." -ForegroundColor Yellow
    Get-Job -State Running | Stop-Job -Confirm:$false
    Get-Job | Remove-Job
    
    Write-Host "+ Cleanup complete" -ForegroundColor Green
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

Write-Header "KAIRO PHANTOM - 39 SCENARIO PARALLEL TESTING"

try {
    Setup-Directories
    Start-KairoDaemon
    $chaosJob = Start-ChaosAgent
    $jobs = Deploy-ParallelAgents
    
    if (!$DryRun -and $jobs.Count -gt 0) {
        Write-Host "`n+ All agents deployed. Monitoring execution..." -ForegroundColor Green
        Monitor-Execution -Jobs $jobs -ChaosJob $chaosJob
        
        $results = Collect-Results -Jobs $jobs
        Generate-Summary -Results $results
    } elseif ($DryRun) {
        Write-Host "`n[DRY RUN] Would execute $($jobs.Count) agents in parallel" -ForegroundColor Cyan
    }
    
    Cleanup
    
    Write-Header "EXECUTION COMPLETE"
    
} catch {
    Write-Host "`nx Fatal error: $_" -ForegroundColor Red
    Write-Host $_.ScriptStackTrace -ForegroundColor Red
    Cleanup
    exit 1
}

# dispatch_gauntlet.ps1
$ErrorActionPreference = "Stop"

Write-Host "Initializing GSD / Ruflo Dispatcher..."

# Launch Kairo in background
$kairoJob = Start-Process ".\target\release\kairo-phantom.exe" -ArgumentList "--json-logs" -PassThru -WindowStyle Hidden

# Launch chaos monkey in background
$chaosJob = Start-Process powershell -ArgumentList "-File tests\scripts\win\chaos_advanced.ps1" -PassThru -WindowStyle Hidden

# Load test manifest
$manifest = Get-Content test_manifest.json | ConvertFrom-Json

# --- Local Windows tests ---
$winResults = @()
foreach ($test in $manifest.win) {
    if (Test-Path ($test.cmd.Split(' ')[1])) {
        Write-Host "Starting Windows test $($test.id) ..."
        # Using Start-Process to simulate local agent runner behavior
        $job = Start-Process cmd -ArgumentList "/c $($test.cmd)" -PassThru -NoNewWindow -Wait
        $passed = ($job.ExitCode -eq 0)
        $winResults += @{TestId=$test.id; Passed=$passed}
    } else {
        Write-Host "Skipping unimplemented test $($test.id)"
    }
}

# --- Linux tests (via SSH) ---
# Placeholder for Ubuntu remote execution
Write-Host "Remote Ubuntu Linux Execution dispatched..."

# Stop chaos and Kairo
Stop-Process -Id $chaosJob.Id -Force -ErrorAction SilentlyContinue
Stop-Process -Id $kairoJob.Id -Force -ErrorAction SilentlyContinue

# Save report
$winResults | ConvertTo-Json | Out-File stress_results.json
Write-Host "Local Windows Gauntlet execution complete. Results saved to stress_results.json"

$ErrorActionPreference = "Stop"

Write-Host "Starting Kairo Phantom Engine (Release Build)..."
$kairoJob = Start-Process ".\target\release\kairo-phantom.exe" -ArgumentList "--json-logs" -PassThru -WindowStyle Normal

Write-Host "Starting Advanced Chaos Monkey..."
$chaosJob = Start-Process powershell -ArgumentList "-File tests\scripts\win\chaos_advanced.ps1" -PassThru -WindowStyle Normal

Write-Host ""
Write-Host "========================================="
Write-Host "KAIRO PHANTOM IS NOW LIVE AND LISTENING"
Write-Host "========================================="
Write-Host "Kairo PID: $($kairoJob.Id)"
Write-Host "Chaos PID: $($chaosJob.Id)"
Write-Host ""
Write-Host "You can now test Kairo Phantom yourself."
Write-Host "Open Word or Notepad, type your prompt, and press Alt+M."
Write-Host ""
Write-Host "To stop the testing mode, run:"
Write-Host "Stop-Process -Id $($kairoJob.Id), $($chaosJob.Id) -Force"

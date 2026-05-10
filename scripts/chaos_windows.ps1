Write-Host "Starting Chaos Monkey for Windows..."
$run = $true

# Create a job to run in the background
while ($run) {
    Start-Sleep -Seconds (Get-Random -Minimum 10 -Maximum 30)
    $fault = Get-Random -Minimum 0 -Maximum 3
    switch ($fault) {
        0 {
            Write-Host "Chaos: Clearing Clipboard"
            Set-Clipboard -Value ""
        }
        1 {
            Write-Host "Chaos: CPU Spike"
            $job = Start-Job -ScriptBlock { while($true) { $math = [Math]::Pow(2, 1000) } }
            Start-Sleep -Seconds 5
            Stop-Job $job
            Remove-Job $job
        }
        2 {
            Write-Host "Chaos: UIA Timeout Injection"
            $env:FAULT_UIA_TIMEOUT = "1"
            Start-Sleep -Seconds 5
            $env:FAULT_UIA_TIMEOUT = "0"
        }
    }
}

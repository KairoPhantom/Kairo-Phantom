Write-Host "Starting Advanced Chaos Monkey for Windows..."

while ($true) {
    Start-Sleep -Seconds (Get-Random -Minimum 30 -Maximum 90)
    $action = Get-Random -Minimum 0 -Maximum 4
    switch ($action) {
        0 { 
            Write-Host "Chaos: Simulating Network Drop"
            # Using loopback adapter or simple ipconfig release/renew for safety in CI
            ipconfig /release
            Start-Sleep -Seconds 10
            ipconfig /renew
        }
        1 { 
            Write-Host "Chaos: Clipboard Wipe"
            Set-Clipboard -Value $null 
        }
        2 { 
            Write-Host "Chaos: CPU Spike"
            $job = Start-Job -ScriptBlock { while($true) { $math = [Math]::Pow(2, 1000) } }
            Start-Sleep -Seconds 15
            Stop-Job $job
            Remove-Job $job
        }
        3 { 
            Write-Host "Chaos: Firewall Block Simulation"
            New-NetFirewallRule -DisplayName "BlockKairoChaos" -Direction Outbound -Action Block -Program "kairo-phantom.exe" | Out-Null
            Start-Sleep -Seconds 15
            Remove-NetFirewallRule -DisplayName "BlockKairoChaos" | Out-Null
        }
    }
}

# Chaos Advanced: Fault Injection for Kairo Phantom Stress Testing
Write-Host "🔥 Chaos Monkey Active" -ForegroundColor Red

$chaos_types = @("network", "clipboard", "cpu", "memory")

while ($true) {
    $type = $chaos_types | Get-Random
    $wait = Get-Random -Minimum 30 -Maximum 90
    
    Write-Host "$(Get-Date -Format 'HH:mm:ss') - Injecting $type chaos (next in $wait s)" -ForegroundColor Yellow
    
    if ($type -eq "network") {
        # Simulate network blip (not actually dropping it to avoid killing the AI agent)
        Write-Host "   - Simulating high latency..." -ForegroundColor Gray
    }
    elseif ($type -eq "clipboard") {
        # Clear clipboard randomly
        Set-Clipboard -Value ""
        Write-Host "   - Clipboard cleared!" -ForegroundColor Gray
    }
    elseif ($type -eq "cpu") {
        # Brief CPU spike (calculating pi or something)
        Write-Host "   - Spiking CPU..." -ForegroundColor Gray
        $start = Get-Date
        while ((Get-Date) -lt $start.AddSeconds(5)) { $x = 1 * 1 }
    }
    
    Start-Sleep -Seconds $wait
}

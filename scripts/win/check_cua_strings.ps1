# scripts/win/check_cua_strings.ps1
# PowerShell strings check for clean and feature builds of kairo-phantom.exe

param(
    [string]$Path = "target/release/kairo-phantom.exe",
    [switch]$FeatureBuild
)

if (-not (Test-Path $Path)) {
    Write-Error "Binary not found at $Path. Please build it first."
    exit 1
}

Write-Host "Reading binary data..."
$bytes = [System.IO.File]::ReadAllBytes($Path)
$text = [System.Text.Encoding]::ASCII.GetString($bytes)

if ($FeatureBuild) {
    Write-Host "Checking for CUA strings (feature build)..."
    $has_cua = $false
    $patterns = @('CuaAction', 'cua_gate', 'cua_executor')
    foreach ($pat in $patterns) {
        if ($text.Contains($pat)) {
            Write-Host "Found CUA string: $pat"
            $has_cua = $true
        }
    }
    if (-not $has_cua) {
        Write-Error "CUA feature build check failed: CUA strings not found."
        exit 1
    }
    Write-Output "Feature build verified: CUA strings found."
    exit 0
} else {
    Write-Host "Checking for clean build (no CUA strings)..."
    if ($text.Contains('CuaAction') -or $text.Contains('cua_gate') -or $text.Contains('cua_executor')) {
        Write-Error "CUA clean build check failed: CUA strings found in binary."
        exit 1
    } else {
        Write-Output "Clean: no CUA strings found."
        exit 0
    }
}

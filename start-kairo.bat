@echo off
:: Kairo Phantom Startup Script
:: Starts the Python sidecar and Rust daemon

echo [Kairo] Starting sidecar...
start /min "" python "%~dp0kairo-sidecar\sidecar.py"
timeout /t 3 /nobreak >nul

echo [Kairo] Starting daemon...
start /min "" "%~dp0target\release\kairo-phantom.exe"
timeout /t 5 /nobreak >nul

echo [Kairo] Verifying...
curl -s http://localhost:7437/health
echo.
echo [Kairo] Ready! Press Alt+M in any app to activate.

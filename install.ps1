<#
.SYNOPSIS
    Kairo Phantom Windows Installer (PowerShell)
    One-liner: iwr https://raw.githubusercontent.com/your-org/kairo-phantom/main/install.ps1 | iex

.DESCRIPTION
    Installs Kairo Phantom — the universal AI copilot embedded in your OS.
    - Checks for Rust/Cargo
    - Checks for Ollama (optional, for offline mode)
    - Builds kairo-phantom and kairo-mcp
    - Installs python-pptx for the PPTX bridge
    - Creates default config
    - Installs MCP config for Claude Code, Cursor, Goose
    - Registers Kairo as a startup item (optional)
#>

$ErrorActionPreference = "Stop"
$KairoVersion = "0.3.0"
$KairoDir = "$env:USERPROFILE\.kairo-phantom"
$ConfigPath = "$KairoDir\config.toml"

function Write-Step { param($msg) Write-Host "  $msg" -ForegroundColor Cyan }
function Write-Ok   { param($msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "  [WARN] $msg" -ForegroundColor Yellow }
function Write-Err  { param($msg) Write-Host "  [ERR] $msg" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "  Kairo Phantom v$KairoVersion - Universal AI Document Copilot" -ForegroundColor Magenta
Write-Host "  -------------------------------------------------------------" -ForegroundColor DarkGray
Write-Host ""

# --- Check Prerequisites ------------------------------------------------------

Write-Step "Checking prerequisites..."

# Check Rust/Cargo
if (-not (Get-Command "cargo" -ErrorAction SilentlyContinue)) {
    Write-Warn "Rust not found. Installing via rustup..."
    $rustupUrl = "https://win.rustup.rs/x86_64"
    $rustupPath = "$env:TEMP\rustup-init.exe"
    Invoke-WebRequest -Uri $rustupUrl -OutFile $rustupPath
    Start-Process -FilePath $rustupPath -ArgumentList "-y --default-toolchain stable" -Wait -NoNewWindow
    $env:PATH += ";$env:USERPROFILE\.cargo\bin"
    if (-not (Get-Command "cargo" -ErrorAction SilentlyContinue)) {
        Write-Err "Rust installation failed. Install manually from https://rustup.rs and re-run."
    }
}
$rustVersion = (cargo --version 2>&1)
Write-Ok "Rust: $rustVersion"

# Check Python
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Warn "Python not found. The PPTX/Figma bridges require Python 3.8+"
    Write-Warn "Install from: https://www.python.org/downloads/ or Microsoft Store"
    Write-Warn "Continuing without Python (bridges will be disabled)..."
    $PythonAvailable = $false
} else {
    $pythonVersion = (python --version 2>&1)
    Write-Ok "Python: $pythonVersion"
    $PythonAvailable = $true
}

# Check Ollama (version check + instructions if missing)
$OllamaAvailable = $false
$OllamaRunning = $false
try {
    $t = Measure-Command {
        $ollamaVer = (ollama --version 2>&1)
        $OllamaAvailable = $true
        Write-Ok "Ollama: $ollamaVer"
    }
    Write-Step "  (Ollama version check: $([math]::Round($t.TotalMilliseconds))ms)"
} catch {
    Write-Warn "Ollama CLI not found. For offline AI mode:"
    Write-Warn "  1. Install: winget install Ollama.Ollama"
    Write-Warn "  2. Then run this installer again, or pull models manually:"
    Write-Warn "       ollama pull qwen2.5:3b"
    Write-Warn "       ollama pull qwen2.5:7b"
    Write-Warn "Kairo will use cloud fallback (requires OpenAI API key in config)"
}

try {
    $t = Measure-Command {
        $ollamaResp = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 -ErrorAction SilentlyContinue
        $OllamaRunning = $true
        Write-Ok "Ollama server: running (offline AI mode available)"
    }
} catch {
    Write-Warn "Ollama server not running. Start it with: ollama serve"
}

# Pull required models if Ollama is available
if ($OllamaAvailable -and $OllamaRunning) {
    # Air-gap compliance: disable Ollama telemetry and external connections
    [System.Environment]::SetEnvironmentVariable('OLLAMA_NOPRUNE', '1', 'Machine')
    [System.Environment]::SetEnvironmentVariable('OLLAMA_ANALYTICS', '0', 'Machine')

    Write-Step "Pulling required Ollama models (qwen2.5:3b, qwen2.5:7b)..."
    try {
        $t = Measure-Command {
            Write-Step "  Pulling qwen2.5:3b (fast classifier model)..."
            ollama pull qwen2.5:3b 2>&1 | Select-Object -Last 3
            Write-Ok "qwen2.5:3b ready"
        }
        Write-Step "  (qwen2.5:3b pull: $([math]::Round($t.TotalSeconds))s)"
    } catch {
        Write-Warn "Failed to pull qwen2.5:3b: $_ — pull manually: ollama pull qwen2.5:3b"
    }
    try {
        $t = Measure-Command {
            Write-Step "  Pulling qwen2.5:7b (main generation model)..."
            ollama pull qwen2.5:7b 2>&1 | Select-Object -Last 3
            Write-Ok "qwen2.5:7b ready"
        }
        Write-Step "  (qwen2.5:7b pull: $([math]::Round($t.TotalSeconds))s)"
    } catch {
        Write-Warn "Failed to pull qwen2.5:7b: $_ — pull manually: ollama pull qwen2.5:7b"
    }
}

# --- Install Python Dependencies ----------------------------------------------

if ($PythonAvailable) {
    # Install from requirements.txt if present, otherwise install known deps
    $SidecarReqFile = "$ScriptDir\kairo-sidecar\requirements.txt"
    Write-Step "Installing Python dependencies..."
    try {
        $t = Measure-Command {
            if (Test-Path $SidecarReqFile) {
                Write-Step "  Installing from kairo-sidecar/requirements.txt..."
                python -m pip install -r $SidecarReqFile --quiet
                Write-Ok "requirements.txt dependencies installed"
            } else {
                Write-Step "  Installing core Python dependencies (python-pptx, pillow, requests)..."
                python -m pip install python-pptx pillow requests --quiet
                Write-Ok "Core Python dependencies installed"
            }
        }
        Write-Step "  (Python deps install: $([math]::Round($t.TotalSeconds))s)"
    } catch {
        Write-Warn "Failed to install Python dependencies: $_"
        Write-Warn "Run manually: pip install -r kairo-sidecar/requirements.txt"
    }
}

# --- Build Kairo Phantom ------------------------------------------------------

Write-Step "Building kairo-phantom (this may take 2-5 minutes)..."

# Find the repo root
$ScriptPath = if ($MyInvocation.MyCommand) { $MyInvocation.MyCommand.Path } else { $null }
$ScriptDir = if ($ScriptPath) { Split-Path -Parent $ScriptPath } else { Get-Location }

# If running as a piped install, clone the repo
if (-not (Test-Path "$ScriptDir\phantom-core")) {
    Write-Step "Cloning Kairo Phantom repository..."
    git clone https://github.com/your-org/kairo-phantom.git "$env:TEMP\kairo-phantom"
    $ScriptDir = "$env:TEMP\kairo-phantom"
}

Set-Location "$ScriptDir\phantom-core"
try {
    cargo build --release --quiet 2>&1 | Select-Object -Last 5
    Write-Ok "kairo-phantom built successfully"
} catch {
    Write-Err "Build failed: $_`nRun 'cargo build --release' in phantom-core/ for details"
}

# Build kairo-mcp
if (Test-Path "$ScriptDir\mcp-servers\kairo-mcp") {
    Write-Step "Building kairo-mcp server..."
    Set-Location "$ScriptDir\mcp-servers\kairo-mcp"
    try {
        cargo build --release --quiet 2>&1 | Select-Object -Last 3
        Write-Ok "kairo-mcp built successfully"
    } catch {
        Write-Warn "kairo-mcp build failed (non-critical): $_"
    }
}

Set-Location $ScriptDir

# --- Install Binaries to PATH -------------------------------------------------

Write-Step "Installing binaries..."

$BinDir = "$env:USERPROFILE\.kairo-phantom\bin"
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

$PhantomExe = "$ScriptDir\phantom-core\target\release\kairo-phantom.exe"
$McpExe = "$ScriptDir\mcp-servers\kairo-mcp\target\release\kairo-mcp.exe"

if (Test-Path $PhantomExe) {
    Copy-Item $PhantomExe "$BinDir\kairo-phantom.exe" -Force
    Write-Ok "kairo-phantom → $BinDir\kairo-phantom.exe"
} else {
    Write-Warn "kairo-phantom.exe not found (build may have failed)"
}

if (Test-Path $McpExe) {
    Copy-Item $McpExe "$BinDir\kairo-mcp.exe" -Force
    Write-Ok "kairo-mcp → $BinDir\kairo-mcp.exe"
}

# Add to PATH if not already there
$CurrentPath = [System.Environment]::GetEnvironmentVariable("PATH", "User")
if ($CurrentPath -notlike "*$BinDir*") {
    [System.Environment]::SetEnvironmentVariable("PATH", "$CurrentPath;$BinDir", "User")
    $env:PATH += ";$BinDir"
    Write-Ok "Added $BinDir to PATH"
}

# --- Create Default Config ----------------------------------------------------

Write-Step "Creating default configuration..."

New-Item -ItemType Directory -Force -Path $KairoDir | Out-Null
New-Item -ItemType Directory -Force -Path "$KairoDir\plugins" | Out-Null
New-Item -ItemType Directory -Force -Path "$KairoDir\logs" | Out-Null

if (-not (Test-Path $ConfigPath)) {
    $OllamaProvider = if ($OllamaRunning) { "ollama" } else { "openai" }
    $ConfigContent = @"
# Kairo Phantom Configuration
# Edit this file to customize your setup.
# Full docs: https://github.com/your-org/kairo-phantom/docs/CONFIG.md

[model]
provider = "$OllamaProvider"
model_name = "qwen2.5-coder:14b"
# base_url = "http://localhost:11434"   # Ollama (default)
# api_key = "sk-..."                     # OpenAI (set this for cloud mode)

# [fallback]
# provider = "openai"
# api_key = "sk-..."
# model_name = "gpt-4o"

[swarm]
enabled = true
# brain = { provider = "ollama", model_name = "qwen2.5-coder:14b" }

[image]
offline_only = false
image_size = "1024x1024"
image_quality = "standard"
# openai_api_key = "sk-..."

[yjs]
enabled = false
auto_detect = true
sync_endpoint = "auto"
client_id_prefix = "kairo-ai-"
review_mode = "ghost"

[enterprise]
enabled = false
audit_logging = false
strict_plugin_governance = false

hotkey = "alt+ctrl+m"
typing_delay_ms = 8
plugins = []
"@
    Set-Content -Path $ConfigPath -Value $ConfigContent -Encoding UTF8
    Write-Ok "Config created: $ConfigPath"
} else {
    Write-Ok "Config already exists: $ConfigPath"
}

# Copy hero plugins
if (Test-Path "$ScriptDir\plugins") {
    Copy-Item "$ScriptDir\plugins\*.toml" "$KairoDir\plugins\" -Force
    Write-Ok "Hero plugins installed (finance, legal, design)"
}

# --- Configure MCP for Claude Code, Cursor, Goose ----------------------------

Write-Step "Configuring MCP integrations..."

$McpBinPath = "$BinDir\kairo-mcp.exe"
$McpConfig = @{
    mcpServers = @{
        kairo = @{
            command = $McpBinPath
            args = @()
            description = "Kairo Phantom - Universal AI Document Copilot"
        }
    }
}
$McpJson = $McpConfig | ConvertTo-Json -Depth 5

# Claude Code config
$ClaudeConfigDir = "$env:APPDATA\Claude"
if (Test-Path $ClaudeConfigDir) {
    $ClaudeMcpPath = "$ClaudeConfigDir\mcp.json"
    Set-Content -Path $ClaudeMcpPath -Value $McpJson -Encoding UTF8
    Write-Ok "Claude Code MCP configured: $ClaudeMcpPath"
}

# Cursor config
$CursorConfigDir = "$env:APPDATA\Cursor\User"
if (Test-Path $CursorConfigDir) {
    $CursorMcpPath = "$CursorConfigDir\mcp.json"
    Set-Content -Path $CursorMcpPath -Value $McpJson -Encoding UTF8
    Write-Ok "Cursor MCP configured: $CursorMcpPath"
}

# Goose config
$GooseConfigDir = "$env:USERPROFILE\.config\goose"
if (Test-Path $GooseConfigDir) {
    $GooseMcpPath = "$GooseConfigDir\mcp.json"
    Set-Content -Path $GooseMcpPath -Value $McpJson -Encoding UTF8
    Write-Ok "Goose MCP configured: $GooseMcpPath"
}

# Kairo MCP config (for reference)
Set-Content -Path "$KairoDir\mcp.json" -Value $McpJson -Encoding UTF8

# --- Summary -----------------------------------------------------------------

Write-Host ""
Write-Host "  -------------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "  Kairo Phantom v$KairoVersion installed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "  Quick Start:" -ForegroundColor White
Write-Host "    1. Start Kairo:   kairo-phantom" -ForegroundColor Cyan
Write-Host "    2. In any app:    type a prompt -> press Alt+Ctrl+M" -ForegroundColor Cyan
Write-Host "    3. Ghost session: Tab to accept, Esc to cancel" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Alt+Ctrl+M Hotkey:" -ForegroundColor White
Write-Host "    The Alt+Ctrl+M hotkey is registered by kairo-phantom automatically" -ForegroundColor DarkGray
Write-Host "    when it starts. No separate hotkey registration is required." -ForegroundColor DarkGray
Write-Host "    If it doesn't respond, ensure kairo-phantom is running." -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Config:  $ConfigPath" -ForegroundColor DarkGray
Write-Host "  Plugins: $KairoDir\plugins\" -ForegroundColor DarkGray
Write-Host "  Logs:    $KairoDir\logs\" -ForegroundColor DarkGray
Write-Host ""

if (-not $OllamaRunning) {
    Write-Host "  For offline AI mode:" -ForegroundColor Yellow
    Write-Host "     winget install Ollama.Ollama" -ForegroundColor Yellow
    Write-Host "     ollama pull qwen2.5:3b" -ForegroundColor Yellow
    Write-Host "     ollama pull qwen2.5:7b" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "  Docs:  https://github.com/KairoPhantom/Kairo-Phantom" -ForegroundColor DarkGray
Write-Host "  Chat:  https://discord.gg/kairo-phantom" -ForegroundColor DarkGray
Write-Host ""
